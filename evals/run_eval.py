"""Routing eval runner: python evals/run_eval.py [--model NAME] [--compare] [--only ID ...] [--delay S].

Runs every case of evals/cases.yaml on a fresh agent thread and checks only the LAST answer plus
the tools called across all turns of the case.
"""

import argparse
import os
import re
import sys
import time
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CASES_FILE = Path(__file__).resolve().parent / "cases.yaml"
RESULTS_DIR = Path(__file__).resolve().parent / "results"
RATE_LIMIT_WAIT = 60  # seconds; free tiers are per-minute
RATE_LIMIT_MARKERS = ("429", "resource_exhausted", "rate")


def _same(expected, actual) -> bool:
    """Numbers compare numerically (the model may send "1000" or 1000), everything else as strings."""
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        try:
            return Decimal(str(actual)) == Decimal(str(expected))
        except InvalidOperation:
            return False
    return str(actual).strip() == str(expected).strip()


def check_case(case: dict, turns: list) -> list[str]:
    """Failure reasons for one case; empty list = pass. `turns` need .text, .tool_calls, .error."""
    failures = []
    calls = [c for t in turns for c in t.tool_calls]
    names = {c.name for c in calls}

    for t in turns:
        if t.error:
            failures.append(f"fallback used: {t.error}")

    alternatives = case.get("tools_any_of")
    if alternatives is not None:
        ok = any((not calls) if not alt else set(alt) <= names for alt in alternatives)
        if not ok:
            failures.append(f"tools {sorted(names) or 'none'} match none of {alternatives}")

    for tool, expected in (case.get("args") or {}).items():
        made = [c for c in calls if c.name == tool]
        # A tool the case does not require (an alternative without it) is not checked here.
        if made and not any(all(k in c.args and _same(v, c.args[k]) for k, v in expected.items()) for c in made):
            failures.append(f"no {tool} call with args {expected}")

    answer = turns[-1].text.lower() if turns else ""
    failures += [f"answer lacks {s!r}" for s in case.get("answer_contains", []) if s.lower() not in answer]
    failures += [f"answer contains {s!r}" for s in case.get("answer_not_contains", []) if s.lower() in answer]
    return failures


def _is_rate_limited(turns: list) -> bool:
    return any(t.error and any(m in t.error.lower() for m in RATE_LIMIT_MARKERS) for t in turns)


def run_case(agent, case: dict):
    from emporio import tools
    from emporio.agent import run_turn

    tools.set_now(datetime.fromisoformat(case["now"]) if case.get("now") else None)
    thread = f"eval-{case['id']}-{time.time_ns()}"
    return [run_turn(agent, thread, message) for message in case["messages"]]


def run_model(model: str, cases: list[dict], delay: float) -> list[dict]:
    from emporio.agent import build_agent

    agent = build_agent(model)
    results = []
    for i, case in enumerate(cases):
        if i:
            time.sleep(delay)
        start = time.time()
        turns = run_case(agent, case)
        if _is_rate_limited(turns):
            print(f"  rate limited on {case['id']}; waiting {RATE_LIMIT_WAIT}s and retrying once", file=sys.stderr)
            time.sleep(RATE_LIMIT_WAIT)
            turns = run_case(agent, case)
        failures = check_case(case, turns)
        called = [c.name for t in turns for c in t.tool_calls]
        results.append({"id": case["id"], "pass": not failures, "reasons": failures, "tools": called,
                        "seconds": time.time() - start})
        print(f"  {case['id']}: {'PASS' if not failures else 'FAIL'}", file=sys.stderr)
    return results


def table(results: list[dict]) -> str:
    lines = [f"{'case':36} {'':4} {'sec':>5}  tools / reasons"]
    for r in results:
        lines.append(f"{r['id']:36} {'PASS' if r['pass'] else 'FAIL'} {r['seconds']:5.1f}  "
                     f"{', '.join(r['tools']) or '-'}" + "".join(f"\n{'':47}! {x}" for x in r["reasons"]))
    return "\n".join(lines)


def score(results: list[dict]) -> str:
    return f"{sum(r['pass'] for r in results)}/{len(results)}"


def write_report(model: str, results: list[dict], delay: float) -> Path:
    from emporio.agent import DEFAULT_RECURSION_LIMIT

    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", model).strip("-")
    rows = "\n".join(
        f"| {r['id']} | {'PASS' if r['pass'] else 'FAIL'} | {'; '.join(r['reasons']) or '-'} | "
        f"{', '.join(r['tools']) or '-'} | {r['seconds']:.1f} |" for r in results)
    text = (f"# Routing eval: {model}\n\n- Run date: {date.today()}\n"
            f"- Config: recursion_limit={DEFAULT_RECURSION_LIMIT}, delay={delay}s, cases={CASES_FILE.name}\n"
            f"- Score: **{score(results)}**\n\n| case | result | reasons | tools | seconds |\n|---|---|---|---|---|\n{rows}\n")
    RESULTS_DIR.mkdir(exist_ok=True)
    path = RESULTS_DIR / f"{slug}.md"
    path.write_text(text, encoding="utf-8")
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model", help="model name (default: $EMPORIO_MODEL)")
    parser.add_argument("--compare", action="store_true", help="also run $EMPORIO_COMPARE_MODEL")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these case ids")
    parser.add_argument("--delay", type=float, default=5.0, help="seconds between cases (default 5)")
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")  # lazy: keep check_case importable before the agent exists
    cases = yaml.safe_load(CASES_FILE.read_text(encoding="utf-8"))
    if args.only:
        unknown = set(args.only) - {c["id"] for c in cases}
        if unknown:
            parser.error(f"unknown case ids: {sorted(unknown)}")
        cases = [c for c in cases if c["id"] in args.only]

    models = [args.model or os.environ.get("EMPORIO_MODEL", "")]
    if args.compare:
        models.append(os.environ.get("EMPORIO_COMPARE_MODEL", ""))
    if not all(models):
        parser.error("no model: pass --model or set EMPORIO_MODEL (and EMPORIO_COMPARE_MODEL for --compare)")

    all_results = {}
    for model in models:
        print(f"== {model}", file=sys.stderr)
        all_results[model] = run_model(model, cases, args.delay)
        print(f"\n{model}\n{table(all_results[model])}\n\nScore: {score(all_results[model])}")
        print(f"Report: {write_report(model, all_results[model], args.delay)}")

    if args.compare:
        print("\nSide by side")
        print(f"{'case':36} " + " ".join(f"{m[:28]:28}" for m in models))
        for i, case in enumerate(cases):
            print(f"{case['id']:36} " + " ".join(
                f"{'PASS' if all_results[m][i]['pass'] else 'FAIL':28}" for m in models))
        print(f"{'score':36} " + " ".join(f"{score(all_results[m]):28}" for m in models))
    return 0


if __name__ == "__main__":
    sys.exit(main())
