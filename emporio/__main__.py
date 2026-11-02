"""Command line: chat with Lia, or replay a conversation script into a Markdown transcript.

    python -m emporio [--debug] [--now ISO] [--model NAME]
    python -m emporio --script examples/scripts/01_catalog.txt --out examples/01_catalog.md
"""

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from emporio import tools
from emporio.agent import Turn, build_agent, resolve_model_name, run_turn

EXIT_WORDS = {"exit", "quit"}


def parse_script(text: str) -> tuple[dict[str, str], list[str]]:
    """Header lines `# key: value` (title, demonstrates, now), then one customer message per line."""
    headers, messages = {}, []
    for line in filter(None, map(str.strip, text.splitlines())):
        if line.startswith("#") and not messages:
            key, _, value = line[1:].partition(":")
            headers[key.strip()] = value.strip()
        else:
            messages.append(line)
    return headers, messages


def demo_lines(turn: Turn) -> list[str]:
    """System lines printed outside Lia's speech, so nobody mistakes the stub for a real ticket."""
    return [
        f"[demo] ticket {call.result['protocol']} saved to tickets.jsonl - stub, no real notification sent"
        for call in turn.tool_calls
        if call.name == "handoff_to_human" and isinstance(call.result, dict) and "protocol" in call.result
    ]


def debug_lines(turn: Turn) -> list[str]:
    lines = []
    for call in turn.tool_calls:
        result = json.dumps(call.result, ensure_ascii=False)
        lines.append(f"  [tool] {call.name} {json.dumps(call.args, ensure_ascii=False)} -> {_short(result)}")
    return [*lines, f"  [{turn.seconds:.1f} s]"]


def _short(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[:limit] + "..."


def chat(agent, debug: bool) -> None:
    thread_id = uuid4().hex  # memory lives only in this session, by design
    print("Lia, the Empório da Música virtual assistant. Type 'exit' to quit.\n")
    try:
        while (text := input("You: ").strip()).lower() not in EXIT_WORDS:
            if not text:
                continue
            turn = run_turn(agent, thread_id, text)
            print(f"Lia: {turn.text}")
            for line in demo_lines(turn) + (debug_lines(turn) if debug else []):
                print(line)
            if turn.error:
                print(f"  [error] {turn.error.splitlines()[0]}", file=sys.stderr)
            print()
    except (EOFError, KeyboardInterrupt):
        print()


def transcript(agent, headers: dict, messages: list[str], model: str, now: datetime | None, command: str) -> str:
    clock = f"fixed at {now:%Y-%m-%d %H:%M} (America/Campo_Grande)" if now else "real time"
    out = [
        f"# {headers.get('title', 'Conversation')}",
        "",
        f"**Scenario:** {headers.get('demonstrates', '-')}",
        "",
        f"- Model: `{model}`",
        f"- Store clock: {clock}",
        f"- Generated: {date.today():%Y-%m-%d}",
        f"- Command: `{command}`",
    ]
    thread_id = uuid4().hex
    for number, message in enumerate(messages, 1):
        turn = run_turn(agent, thread_id, message)
        out += ["", "---", "", f"### Turn {number}", "", f"**Customer:** {message}", ""]
        calls = [f"- Tool call: `{c.name}({json.dumps(c.args, ensure_ascii=False)})`" for c in turn.tool_calls]
        out += calls or ["_No tool call._"]
        out += ["", "**Lia:**", "", *(f"> {line}" for line in turn.text.splitlines())]
        out += [f"\n`{line}`" for line in demo_lines(turn)]
        if turn.error:
            out.append(f"\n`[error] {turn.error.splitlines()[0]}`")
    return "\n".join(out) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(
        prog="python -m emporio", description="Chat with Lia, the Empório da Música virtual assistant."
    )
    parser.add_argument("--debug", action="store_true", help="after each answer, show tool calls and latency")
    parser.add_argument("--script", type=Path, help="conversation script to replay (see examples/scripts)")
    parser.add_argument("--out", type=Path, help="Markdown transcript written by --script")
    parser.add_argument(
        "--now", type=datetime.fromisoformat, help="fix the store clock, Campo Grande time (e.g. 2026-11-01T21:30)"
    )
    parser.add_argument("--model", help="override EMPORIO_MODEL, in provider:model format")
    args = parser.parse_args(argv)
    if bool(args.script) != bool(args.out):
        parser.error("--script and --out go together")

    headers, messages = parse_script(args.script.read_text(encoding="utf-8")) if args.script else ({}, [])
    now = args.now or (datetime.fromisoformat(headers["now"]) if "now" in headers else None)
    tools.set_now(now)
    try:
        model = resolve_model_name(args.model)
        agent = build_agent(model)
    except Exception as e:  # missing model name, API key or provider package
        print(f"Cannot start the model ({type(e).__name__}): set EMPORIO_MODEL and its API key in .env "
              "(see .env.example)", file=sys.stderr)
        return 2

    if not args.script:
        chat(agent, args.debug)
        return 0
    command = "python -m emporio " + " ".join(argv)  # display only; shlex.join would mangle Windows paths
    args.out.write_text(transcript(agent, headers, messages, model, now, command), encoding="utf-8")
    print(f"Transcript written to {args.out}")
    return 0


if __name__ == "__main__":
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # the Windows console defaults to cp1252 and crashes on emojis
    sys.exit(main())
