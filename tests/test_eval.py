import sys
from pathlib import Path
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals"))
from run_eval import check_case  # noqa: E402


def turn(text="", calls=(), error=None):
    return NS(text=text, tool_calls=[NS(name=n, args=a, result={}) for n, a in calls], error=error)


CASE = {
    "tools_any_of": [[], ["get_store_policy"]],
    "args": {"list_products": {"category": "violoes", "max_price": 1000}},
    "answer_contains": ["R$ 429,90"],
    "answer_not_contains": ["GF-3D"],
}


def test_pass_and_alternatives():
    case = {"tools_any_of": [["find_product"], ["find_product", "handoff_to_human"]]}
    assert check_case(case, [turn("ok", [("find_product", {}), ("handoff_to_human", {})])]) == []


def test_missing_tool():
    assert check_case({"tools_any_of": [["get_order_status"]]}, [turn("x", [("find_product", {})])])


def test_empty_list_expects_no_call():
    case = {"tools_any_of": [[]]}
    assert check_case(case, [turn("x")]) == []
    assert check_case(case, [turn("x", [("find_product", {})])])


def test_tools_from_all_turns_but_last_answer_only():
    case = {"tools_any_of": [["a"]], "answer_contains": ["final"]}
    assert check_case(case, [turn("first", [("a", {})]), turn("Final")]) == []
    assert check_case(case, [turn("final", [("a", {})]), turn("other")])


def test_partial_args_numeric_vs_string():
    case = {"args": CASE["args"]}
    for price in ("1000", 1000, 1000.0):
        assert check_case(case, [turn("", [("list_products", {"category": "violoes", "max_price": price, "x": 1})])]) == []
    assert check_case(case, [turn("", [("list_products", {"category": "violoes", "max_price": 900})])])
    # any call may match; a tool that was not called is not checked here
    assert check_case(case, [turn("", [("list_products", {}), ("list_products", {"category": "violoes", "max_price": 1000})])]) == []
    assert check_case(case, [turn("")]) == []


def test_contains_case_insensitive():
    case = {"answer_contains": ["tuesday"], "answer_not_contains": ["PARIS"]}
    assert check_case(case, [turn("See you TUESDAY")]) == []
    assert len(check_case(case, [turn("paris on monday")])) == 2


def test_fallback_error_fails():
    assert "fallback used: 429" in check_case({}, [turn("sorry", error="429")])[0]
