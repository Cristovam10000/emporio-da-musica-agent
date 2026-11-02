import json
from datetime import date, datetime

import pytest
from pydantic import ValidationError

from emporio import tools
from emporio.tools import find_product, get_order_status, get_store_policy, handoff_to_human, list_products

ORDER_8_EMAIL = "anacarol.ferreira@coldmail.com"  # customer 2, Ana Carolina Ferreira


@pytest.fixture(autouse=True)
def frozen_clock():
    tools.set_now(datetime(2026, 11, 1, 10, 0))
    yield
    tools.set_now(None)


@pytest.fixture
def tickets(tmp_path, monkeypatch):
    path = tmp_path / "tickets.jsonl"
    monkeypatch.setattr(tools, "TICKETS_PATH", path)
    return path


def ids(products):
    return [p["product_id"] for p in products]


# --- find_product / product_view -----------------------------------------------------------


def test_takamine_gd20_is_a_single_match_with_pix_price():
    result = find_product.invoke({"name": "takamine gd20"})
    assert result["ambiguous"] is False
    assert ids(result["matches"]) == [95]
    product = result["matches"][0]
    assert product["list_price"] == "R$ 2.199,00"
    assert product["pix_price"] == "R$ 2.089,05"
    assert product["promotion"] is None
    assert product["split_payment_allowed"] is True


@pytest.mark.parametrize(
    "query, product_id",
    [
        ("Takamine GD20", 95),
        ("takamine gd 20", 95),
        ("takamine gd-20", 95),
        ("takamine GD20 violão", 95),
        ("ohana ck20", 121),
        ("ohana ck-20", 121),
        ("ukulele ohana concert", 121),
        ("martin d-28e", 108),
        ("yamaha c40", 81),
        ("yamaha c 40", 81),
        ("Yamaha F-310", 87),
    ],
)
def test_model_code_separators_do_not_matter(query, product_id):
    result = find_product.invoke({"name": query})
    assert result["ambiguous"] is False
    assert ids(result["matches"]) == [product_id]


@pytest.mark.parametrize("query", ["martin d-28", "martin d28"])
def test_martin_d28_is_ambiguous(query):
    result = find_product.invoke({"name": query})
    assert result["ambiguous"] is True
    assert set(ids(result["matches"])) == {93, 108}


def test_brand_only_lists_all_its_products():
    result = find_product.invoke({"name": "takamine"})
    assert result["ambiguous"] is True
    assert set(ids(result["matches"])) == {95, 100, 105, 115}


def test_unknown_product_returns_no_matches():
    assert find_product.invoke({"name": "saxofone"})["matches"] == []


def test_promotion_price_replaces_pix():
    product = find_product.invoke({"name": "ohana ck-20"})["matches"][0]
    assert product["product_id"] == 121
    assert product["promotion"] == {"percent": 20, "price": "R$ 439,20", "original_price": "R$ 549,00"}
    assert product["pix_price"] is None
    assert product["installments"] == {"max": 5, "value": "R$ 87,84"}  # computed on R$ 439,20


@pytest.mark.parametrize(
    "query, product_id, availability",
    [
        ("giannini gf-3d", 96, "temporarily_unavailable"),
        ("shelby sn-7c", 113, "discontinued"),
        ("ibanez bass 2x", 136, "discontinued"),
        ("kala ka-abp-ctg", 130, "coming_soon"),
    ],
)
def test_availability_labels(query, product_id, availability):
    product = find_product.invoke({"name": query})["matches"][0]
    assert product["product_id"] == product_id
    assert product["availability"] == availability
    assert product["low_stock"] is False  # low_stock only applies to available items


def test_low_stock_flag():
    martin = find_product.invoke({"name": "martin d-28 dreadnought"})["matches"][0]
    assert (martin["product_id"], martin["availability"], martin["low_stock"]) == (93, "available", True)


# --- list_products -------------------------------------------------------------------------


def test_acoustic_guitars_up_to_1000_are_purchasable_and_sorted():
    result = list_products.invoke({"category": "violoes", "max_price": 1000, "limit": 20})
    found = ids(result["products"])
    assert found and 96 not in found and 113 not in found
    prices = [tools._current_price(tools.load_data().products[i]) for i in found]
    assert prices == sorted(prices) and max(prices) <= 1000
    assert all(p["availability"] == "available" for p in result["products"])
    assert result["total_matches"] == len(found)


def test_price_filter_uses_promotion_price():
    # product 121 lists at R$ 549,00 but costs R$ 439,20 with the active promotion
    assert 121 in ids(list_products.invoke({"category": "ukuleles", "max_price": 450})["products"])


def test_string_and_electronics_filters():
    products = list_products.invoke({"strings": "nylon", "electronics": True, "limit": 20})["products"]
    assert products
    assert all(p["specs"]["strings"] == "nylon" and p["specs"]["electronics"] == "yes" for p in products)


def test_limit_caps_products_but_not_total():
    result = list_products.invoke({"limit": 3})
    assert len(result["products"]) == 3 and result["total_matches"] > 3


def test_empty_category_has_a_note():
    result = list_products.invoke({"category": "sopro_metais"})
    assert result["products"] == [] and result["total_matches"] == 0
    assert "no products" in result["note"]


# --- get_order_status ----------------------------------------------------------------------


def test_wrong_contact_and_missing_order_look_the_same():
    wrong_contact = get_order_status.invoke({"order_id": 8, "contact": "someone@else.com"})
    missing_order = get_order_status.invoke({"order_id": 999, "contact": ORDER_8_EMAIL})
    assert wrong_contact == missing_order == {"found": False, "message": "Order not found or the contact does not match."}


@pytest.mark.parametrize("contact", [ORDER_8_EMAIL, " AnaCarol.Ferreira@Coldmail.com ", "+55 67 99654-7821", "67996547821"])
def test_order_8_is_found_and_delayed(contact):
    result = get_order_status.invoke({"order_id": 8, "contact": contact})
    assert result["found"] is True
    assert result["customer_first_name"] == "Ana"
    assert result["status"] == "shipped"
    assert result["estimated_delivery"] == "2026-02-28"
    assert result["delayed"] is True
    assert result["total"] == "R$ 349,90"
    assert result["tracking_code"] == "BRJL5544332BR"
    assert "return_windows" not in result


def test_order_result_has_no_personal_data():
    text = json.dumps(get_order_status.invoke({"order_id": 8, "contact": ORDER_8_EMAIL}), ensure_ascii=False)
    for secret in (ORDER_8_EMAIL, "99654", "7821", "Ferreira", "Campo Grande"):
        assert secret not in text


def test_cancelled_order_has_reason_and_is_not_delayed():
    customer = tools.load_data().customers[tools.load_data().orders[17].customer_id]
    result = get_order_status.invoke({"order_id": 17, "contact": customer.email})
    assert result["status"] == "cancelled" and result["cancellation_reason"] and result["delayed"] is False


def test_received_on_adds_return_windows():
    result = get_order_status.invoke({"order_id": 8, "contact": ORDER_8_EMAIL, "received_on": "2026-10-28"})
    assert result["days_since_receipt"] == 4
    assert result["return_windows"] == {
        "regret": {"deadline": "2026-11-04", "still_open": True},
        "preference_exchange": {"deadline": "2026-11-04", "still_open": True},
        "defect_exchange": {"deadline": "2026-03-17", "still_open": False},  # 30 days from order date
        "legal_warranty": {"deadline": "2027-01-26", "still_open": True},
    }


def test_received_on_in_the_future_is_rejected():
    with pytest.raises(ValidationError):
        get_order_status.invoke({"order_id": 8, "contact": ORDER_8_EMAIL, "received_on": "2026-11-02"})


# --- get_store_policy ----------------------------------------------------------------------


def test_policy_section_is_returned_whole():
    result = get_store_policy.invoke({"topic": "horario"})
    assert result["topic"] == "horario"
    assert "09:00 às 18:00" in result["text"]
    assert "Interpretation notes" in result["text"]
    assert "## pagamento_parcelamento" not in result["text"]


def test_internal_rules_are_not_a_policy_topic():
    with pytest.raises(ValidationError):
        get_store_policy.invoke({"topic": "atendimento_regras"})


# --- handoff_to_human ----------------------------------------------------------------------


def test_handoff_appends_ticket_and_numbers_per_day(tickets):
    args = {"reason": "pedido_atrasado", "summary": "Order 8 is months late.", "order_id": 8}
    first = handoff_to_human.invoke(args)
    second = handoff_to_human.invoke(args)
    assert first == {"protocol": "EMP-20261101-001", "simulated": True, "response_time": "up to 24 business hours"}
    assert second["protocol"] == "EMP-20261101-002"
    lines = tickets.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["protocol"] for line in lines] == ["EMP-20261101-001", "EMP-20261101-002"]
    assert json.loads(lines[0])["order_id"] == 8


def test_handoff_sequence_restarts_next_day(tickets):
    handoff_to_human.invoke({"reason": "outro", "summary": "First day ticket."})
    tools.set_now(datetime(2026, 11, 3, 9, 0))
    assert handoff_to_human.invoke({"reason": "outro", "summary": "Next day ticket."})["protocol"] == "EMP-20261103-001"


# --- validation and serialization ----------------------------------------------------------


@pytest.mark.parametrize(
    "tool, args",
    [
        (list_products, {"max_price": -1}),
        (list_products, {"limit": 50}),
        (list_products, {"category": "acessorios"}),
        (get_order_status, {"order_id": "abc", "contact": ORDER_8_EMAIL}),
        (find_product, {"name": "x"}),
        (handoff_to_human, {"reason": "outro", "summary": "short"}),
    ],
)
def test_invalid_arguments_fail_validation(tool, args):
    with pytest.raises(ValidationError):
        tool.invoke(args)


def test_every_tool_result_is_json_serializable(tickets):
    results = [
        find_product.invoke({"name": "takamine"}),
        list_products.invoke({"limit": 20}),
        list_products.invoke({"category": "sopro_madeiras"}),
        get_order_status.invoke({"order_id": 8, "contact": ORDER_8_EMAIL, "received_on": date(2026, 10, 28)}),
        get_order_status.invoke({"order_id": 1, "contact": "nobody@example.com"}),
        get_store_policy.invoke({"topic": "pagamento_parcelamento"}),
        handoff_to_human.invoke({"reason": "outro", "summary": "Serialization check."}),
    ]
    for result in results:
        json.dumps(result)


def test_tools_list_order():
    assert [t.name for t in tools.TOOLS] == [
        "find_product", "list_products", "get_order_status", "get_store_policy", "handoff_to_human"
    ]
