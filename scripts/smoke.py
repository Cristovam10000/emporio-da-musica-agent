"""Smoke test of the LangChain v1 agent mechanics the project relies on.

Offline (default): a scripted fake chat model, no API key needed.
    .venv\\Scripts\\python scripts/smoke.py
Live: one real tool call with init_chat_model(EMPORIO_MODEL); SKIP if not configured.
    .venv\\Scripts\\python scripts/smoke.py --live
"""

import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, dynamic_prompt
from langchain.chat_models import init_chat_model
from langchain.tools import tool
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.errors import GraphRecursionError
from pydantic import BaseModel, Field


class AddArgs(BaseModel):
    a: int = Field(ge=0)
    b: int = Field(ge=0)


@tool(args_schema=AddArgs)
def add(a: int, b: int) -> int:
    """Add two non-negative integers."""
    return a + b


PROMPT_CALLS: list[str] = []


@dynamic_prompt
def store_prompt(request: ModelRequest) -> str:
    # Computed at call time, once per model call.
    stamp = datetime.now().isoformat()
    PROMPT_CALLS.append(stamp)
    return f"You are a test assistant. Current time: {stamp}"


class ScriptedModel(FakeMessagesListChatModel):
    """Replays scripted responses and records every message list it receives."""

    seen: list[list[BaseMessage]] = []

    def bind_tools(self, tools, **kwargs):
        return self  # the replies are scripted, so the tool schemas are not needed

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        return super()._generate(messages, stop, run_manager, **kwargs)


def call_add(a, b, call_id="call_1") -> AIMessage:
    return AIMessage(content="", tool_calls=[{"name": "add", "args": {"a": a, "b": b}, "id": call_id}])


def build(model, checkpointer=None):
    return create_agent(model, tools=[add], middleware=[store_prompt], checkpointer=checkpointer)


RESULTS: list[bool] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    RESULTS.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {label}{' - ' + detail if detail else ''}")


def offline() -> None:
    # (a) tool call executes and its result goes back to the model
    model = ScriptedModel(responses=[call_add(2, 3), AIMessage(content="It is 5.")])
    out = build(model).invoke({"messages": [{"role": "user", "content": "2+3?"}]})
    tool_msgs = [m for m in model.seen[1] if isinstance(m, ToolMessage)]
    check(
        "(a) tool executes, result returns to model",
        len(tool_msgs) == 1 and tool_msgs[0].content == "5" and out["messages"][-1].content == "It is 5.",
    )

    # (b) invalid argument (a=-1 breaks ge=0) comes back as an error ToolMessage, run continues
    model = ScriptedModel(responses=[call_add(-1, 3), AIMessage(content="Sorry, invalid input.")])
    try:
        out = build(model).invoke({"messages": [{"role": "user", "content": "-1+3?"}]})
        err = [m for m in model.seen[1] if isinstance(m, ToolMessage)][0]
        check(
            "(b) invalid tool argument returns to model as error",
            err.status == "error" and "greater than or equal to 0" in err.content,
            f"status={err.status!r}",
        )
    except Exception as e:  # a crash here is exactly what (b) must rule out
        check("(b) invalid tool argument returns to model as error", False, repr(e))

    # (c) dynamic system prompt, computed per model call
    model = ScriptedModel(responses=[call_add(1, 1), AIMessage(content="2")])
    PROMPT_CALLS.clear()
    build(model).invoke({"messages": [{"role": "user", "content": "1+1?"}]})
    systems = [msgs[0].content for msgs in model.seen]
    check(
        "(c) dynamic prompt computed at call time",
        len(PROMPT_CALLS) == 2 and systems == [f"You are a test assistant. Current time: {s}" for s in PROMPT_CALLS],
        f"{len(PROMPT_CALLS)} prompts built for 2 model calls",
    )

    # (d) recursion_limit stops a model that calls tools forever
    model = ScriptedModel(responses=[call_add(1, 1)])  # cycles: always another tool call
    try:
        build(model).invoke({"messages": [{"role": "user", "content": "loop"}]}, {"recursion_limit": 6})
        check("(d) recursion_limit stops endless tool calls", False, "no exception raised")
    except GraphRecursionError:
        check("(d) recursion_limit stops endless tool calls", True, f"GraphRecursionError after {len(model.seen)} model calls")

    # (e) InMemorySaver keeps history across invokes with the same thread_id
    model = ScriptedModel(responses=[AIMessage(content="Hi Ana."), AIMessage(content="You are Ana.")])
    agent = build(model, checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "t1"}}
    agent.invoke({"messages": [{"role": "user", "content": "I am Ana."}]}, config)
    agent.invoke({"messages": [{"role": "user", "content": "Who am I?"}]}, config)
    second_call = [m.content for m in model.seen[1][1:]]  # skip the system prompt
    check(
        "(e) InMemorySaver keeps history per thread_id",
        second_call == ["I am Ana.", "Hi Ana.", "Who am I?"],
        f"second call saw {len(second_call)} messages",
    )


def live() -> None:
    load_dotenv()
    model_name = os.environ.get("EMPORIO_MODEL", "")
    if not model_name or "<" in model_name:
        print("SKIP live: EMPORIO_MODEL is not set (see .env.example)")
        return
    try:
        model = init_chat_model(model_name, temperature=0)
    except Exception as e:  # missing provider package or API key
        print(f"SKIP live: cannot create {model_name!r}: {e}")
        return
    out = build(model).invoke(
        {"messages": [{"role": "user", "content": "Use the add tool to compute 17 + 25."}]},
        {"recursion_limit": 11},
    )
    tool_msgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    check(
        f"live {model_name}: real tool call",
        any(m.content == "42" for m in tool_msgs),
        f"final answer: {out['messages'][-1].content!r}",
    )


if __name__ == "__main__":
    live() if "--live" in sys.argv else offline()
    sys.exit(0 if all(RESULTS) else 1)
