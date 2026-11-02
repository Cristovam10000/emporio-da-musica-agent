from datetime import datetime
from pathlib import Path

import pytest
import yaml

from emporio.prompts import build_system_prompt
from emporio.rules import TZ

ROOT = Path(__file__).resolve().parent.parent
TOOLS = {"find_product", "list_products", "get_order_status", "get_store_policy", "handoff_to_human"}
CASE_KEYS = {"id", "messages", "now", "tools_any_of", "args", "answer_contains", "answer_not_contains"}
SCRIPTS = sorted((ROOT / "examples" / "scripts").glob("*.txt"))


def test_closed_sunday_night_reopens_tuesday():
    prompt = build_system_prompt(datetime(2026, 11, 1, 21, 30, tzinfo=TZ))
    assert "Sunday 2026-11-01 21:30" in prompt
    assert "Store CLOSED. Reopens Tuesday 2026-11-03 at 09:00." in prompt
    assert "Tomorrow (Monday 2026-11-02): closed." in prompt  # Finados


def test_open_wednesday_until_18():
    prompt = build_system_prompt(datetime(2026, 11, 4, 10, 0))  # naive = Campo Grande time
    assert "Store OPEN until 18:00." in prompt
    assert "Tomorrow (Thursday 2026-11-05): open 09:00-18:00." in prompt


def test_prompt_names_every_tool():
    prompt = build_system_prompt(datetime(2026, 11, 4, 10, 0))
    assert all(name in prompt for name in TOOLS)


def test_eval_cases_schema():
    cases = yaml.safe_load((ROOT / "evals" / "cases.yaml").read_text(encoding="utf-8"))
    assert 10 <= len(cases) <= 12
    assert len({c["id"] for c in cases}) == len(cases)
    for case in cases:
        assert {"id", "messages", "tools_any_of"} <= case.keys() <= CASE_KEYS, case.get("id")
        assert case["messages"] and all(isinstance(m, str) for m in case["messages"])
        assert all(set(alt) <= TOOLS for alt in case["tools_any_of"]), case["id"]
        assert set(case.get("args", {})) <= TOOLS, case["id"]
        if "now" in case:
            datetime.fromisoformat(case["now"])


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_script_headers(path):
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    headers = {}
    for line in lines:
        if not line.startswith("#"):
            break
        key, _, value = line[1:].partition(":")
        headers[key.strip()] = value.strip()
    assert {"title", "demonstrates"} <= headers.keys() <= {"title", "demonstrates", "now"}
    assert all(headers.values())
    if "now" in headers:
        datetime.fromisoformat(headers["now"])
    messages = lines[len(headers):]
    assert messages and not any(m.startswith("#") for m in messages)


def test_five_scripts():
    assert len(SCRIPTS) == 5
