"""Agent loop and CLI, offline: a scripted fake chat model replaces the real provider."""

from datetime import datetime

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from emporio import __main__ as cli
from emporio import tools
from emporio.agent import FALLBACK_MESSAGE, build_agent, run_turn
from emporio.rules import TZ
from scripts.smoke import ScriptedModel


def call(name: str, args: dict, call_id: str) -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": name, "args": args, "id": call_id}])


def answer(text: str) -> AIMessage:
    return AIMessage(content=[{"type": "text", "text": text}])  # Gemini returns content blocks


class FailingModel(ScriptedModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "TICKETS_PATH", tmp_path / "tickets.jsonl")
    yield
    tools.set_now(None)


def test_run_turn_returns_text_and_only_this_turns_calls():
    model = ScriptedModel(responses=[
        call("find_product", {"name": "takamine gd20"}, "c1"), answer("It is R$ 2.199,00."), answer("You're welcome!"),
    ])
    agent = build_agent(model=model)
    first = run_turn(agent, "t1", "How much is the Takamine GD20?")
    second = run_turn(agent, "t1", "Thanks")

    assert first.text == "It is R$ 2.199,00." and first.error is None
    assert [(c.name, c.args) for c in first.tool_calls] == [("find_product", {"name": "takamine gd20"})]
    assert first.tool_calls[0].result["matches"][0]["product_id"] == 95  # parsed JSON, not a string
    assert second.text == "You're welcome!" and second.tool_calls == []


def test_memory_second_turn_sees_the_first():
    model = ScriptedModel(responses=[answer("Hi Ana!"), answer("You are Ana.")])
    agent = build_agent(model=model)
    run_turn(agent, "t1", "I am Ana.")
    run_turn(agent, "t1", "Who am I?")
    assert [m.text for m in model.seen[-1][1:]] == ["I am Ana.", "Hi Ana!", "Who am I?"]  # [0] = system prompt


def test_endless_tool_calls_fall_back_and_leave_a_usable_thread():
    model = ScriptedModel(responses=[call("find_product", {"name": "takamine"}, f"c{i}") for i in range(20)])
    agent = build_agent(model=model)
    turn = run_turn(agent, "t1", "loop")

    assert turn.text == FALLBACK_MESSAGE and turn.error.startswith("GraphRecursionError")
    assert len(turn.tool_calls) == 6 and turn.tool_calls[-1].result == "(not executed)"  # 5 rounds, 6th stopped
    last = agent.get_state({"configurable": {"thread_id": "t1"}}).values["messages"][-1]
    assert isinstance(last, ToolMessage)  # no dangling tool call left for the next turn


def test_model_error_falls_back():
    turn = run_turn(build_agent(model=FailingModel(responses=[])), "t1", "hi")
    assert turn.text == FALLBACK_MESSAGE and "429" in turn.error


def test_parse_script():
    headers, messages = cli.parse_script("# title: Late order\n# demonstrates: handoff\n# now: 2026-11-01T21:30\n\nHi\nOrder 8\n")
    assert headers == {"title": "Late order", "demonstrates": "handoff", "now": "2026-11-01T21:30"}
    assert messages == ["Hi", "Order 8"]


def test_script_transcript_shows_tool_calls_and_demo_line(tmp_path, monkeypatch):
    model = ScriptedModel(responses=[
        answer("Sure! What is the order number?"),
        call("handoff_to_human", {"reason": "pedido_atrasado", "summary": "Order 8 is late", "order_id": 8}, "c1"),
        answer("Done, protocol EMP-20261101-001."),
    ])
    monkeypatch.setattr(cli, "build_agent", lambda name: build_agent(model=model))
    script = tmp_path / "late.txt"
    script.write_text("# title: Late order\n# demonstrates: handoff\n# now: 2026-11-01T21:30\nHi\nOpen a ticket\n")
    out = tmp_path / "late.md"

    assert cli.main(["--script", str(script), "--out", str(out), "--model", "fake:model"]) == 0
    md = out.read_text(encoding="utf-8")
    assert md.startswith("# Late order\n") and "`fake:model`" in md and "2026-11-01 21:30" in md
    assert '`handoff_to_human({"reason": "pedido_atrasado", "summary": "Order 8 is late", "order_id": 8})`' in md
    assert "[demo] ticket EMP-20261101-001 saved to tickets.jsonl - stub, no real notification sent" in md
    assert "> Done, protocol EMP-20261101-001." in md and "### Turn 2" in md


def test_now_flag_sets_the_tools_clock(monkeypatch):
    monkeypatch.setattr(cli, "build_agent", lambda name: build_agent(model=ScriptedModel(responses=[answer("-")])))
    monkeypatch.setattr("builtins.input", lambda prompt: "exit")
    assert cli.main(["--now", "2026-11-03T09:00", "--model", "fake:model"]) == 0
    assert tools.now() == datetime(2026, 11, 3, 9, 0, tzinfo=TZ)


def test_missing_model_exits_2(monkeypatch, capsys):
    monkeypatch.setenv("EMPORIO_MODEL", "")  # load_dotenv does not override variables already set
    assert cli.main([]) == 2
    assert ".env.example" in capsys.readouterr().err
