"""The store agent: LangChain v1 create_agent with the five tools, a per-call system prompt
and in-memory conversation history per thread_id."""

import json
import os
import time
from dataclasses import dataclass

from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRequest, ToolErrorMiddleware, dynamic_prompt
from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from emporio import tools
from emporio.prompts import build_system_prompt, customer_language

DEFAULT_RECURSION_LIMIT = 11  # 5 tool rounds + final answer: each round is 2 graph steps (model, tools)
FALLBACK_MESSAGE = (
    "Desculpe, tive um problema técnico agora. Tente de novo em instantes ou fale com a loja "
    "pelo (67) 3341-4444. / Sorry, I hit a technical problem. Please try again in a moment or "
    "call the store at (67) 3341-4444."
)


@dataclass
class ToolCall:
    name: str
    args: dict
    result: dict | str  # parsed JSON when the tool returned JSON, else the raw string


@dataclass
class Turn:
    text: str
    tool_calls: list[ToolCall]  # only the calls made during this turn, in order
    seconds: float
    error: str | None = None  # set when FALLBACK_MESSAGE was used


@dynamic_prompt
def store_prompt(request: ModelRequest) -> str:
    """Rebuilt per model call: the store status stays current and the reply language follows
    the customer's latest message."""
    latest = next((m.text for m in reversed(request.messages) if isinstance(m, HumanMessage)), "")
    return build_system_prompt(tools.now(), customer_language(latest))


def resolve_model_name(model_name: str | None = None) -> str:
    load_dotenv(tools.ROOT / ".env")
    name = model_name or os.environ.get("EMPORIO_MODEL", "")
    if not name or "<" in name:
        raise ValueError("EMPORIO_MODEL is not set")
    return name


def build_agent(model_name: str | None = None, *, model: BaseChatModel | None = None):
    """`model` injects a ready chat model (tests); otherwise init_chat_model(name or $EMPORIO_MODEL).
    No temperature: Gemini 3.x ignores it and warns."""
    model = model or init_chat_model(resolve_model_name(model_name))
    middleware = [store_prompt, ToolErrorMiddleware(on_error=_tool_failed)]
    return create_agent(model, tools=tools.TOOLS, middleware=middleware, checkpointer=InMemorySaver())


def run_turn(agent, thread_id: str, text: str) -> Turn:
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": DEFAULT_RECURSION_LIMIT}
    start = time.perf_counter()
    try:
        messages = agent.invoke({"messages": [{"role": "user", "content": text}]}, config)["messages"]
        error = None
    except Exception as e:  # GraphRecursionError, provider/network errors, 429 ...
        messages = agent.get_state(config).values.get("messages", [])  # keep the calls made before the error
        error = f"{type(e).__name__}: {e}"
        _close_dangling_calls(agent, config, messages)
    seconds = time.perf_counter() - start
    turn = _this_turn(messages)
    calls = _tool_calls(turn)
    if error or not turn or not isinstance(turn[-1], AIMessage):
        return Turn(FALLBACK_MESSAGE, calls, seconds, error or "no final answer")
    return Turn(turn[-1].text, calls, seconds)


def _close_dangling_calls(agent, config: dict, messages: list[BaseMessage]) -> None:
    """A run stopped after the model asked for tools leaves calls without results in the history;
    providers reject such a thread, so every later turn would fail too. Matched by call id, so a
    partly answered set of parallel calls is closed too."""
    answered = {m.tool_call_id for m in messages if isinstance(m, ToolMessage)}
    missing = [c["id"] for m in messages if isinstance(m, AIMessage) for c in m.tool_calls if c["id"] not in answered]
    if missing:
        agent.update_state(config, {"messages": [ToolMessage("Not executed: the turn was interrupted.", tool_call_id=i) for i in missing]})


def _tool_failed(exc: Exception, request) -> str:
    """An unexpected exception inside a tool goes back to the model as an error result instead of
    crashing the turn. Only the type is shown: the message may carry internal detail."""
    return f"Tool failed ({type(exc).__name__}). Apologize and offer to pass the request to the team."


def _this_turn(messages: list[BaseMessage]) -> list[BaseMessage]:
    """Messages after the latest customer message: the agent never adds HumanMessages itself."""
    last = max((i for i, m in enumerate(messages) if isinstance(m, HumanMessage)), default=-1)
    return messages[last + 1:]


def _tool_calls(messages: list[BaseMessage]) -> list[ToolCall]:
    results = {m.tool_call_id: _parse(m.content) for m in messages if isinstance(m, ToolMessage)}
    return [
        ToolCall(call["name"], call["args"], results.get(call["id"], "(not executed)"))
        for m in messages if isinstance(m, AIMessage)
        for call in m.tool_calls
    ]


def _parse(content) -> dict | str:
    try:
        return json.loads(content)
    except (TypeError, ValueError):
        return content
