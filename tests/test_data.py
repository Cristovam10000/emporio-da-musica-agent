from datetime import date
from decimal import Decimal

from emporio.data import load_data, normalize_email, normalize_phone, normalize_text


def test_products_loaded_and_indexed_by_id():
    data = load_data()
    assert len(data.products) == 65
    assert data.products[145].product_id == 145


def test_money_fields_are_decimal():
    data = load_data()
    assert all(isinstance(p.price_brl, Decimal) for p in data.products.values())
    assert all(isinstance(o.total_brl, Decimal) for o in data.orders.values())


def test_takamine_gd20_price():
    product = load_data().products[95]
    assert "Takamine GD20" in product.name
    assert product.price_brl == Decimal("2199")


def test_specs_parsed_to_dict():
    assert load_data().products[81].specs["strings"] == "nylon"


def test_active_promotions_percent():
    active = load_data().active_promotions
    assert {pid: p.discount_percent for pid, p in active.items()} == {
        127: 10,
        121: 20,
        90: 18,
        94: 8,
    }


def test_order_joins_items_and_products():
    data = load_data()
    order = data.orders[8]
    assert order.order_date == date(2026, 2, 15)
    assert order.estimated_delivery == date(2026, 2, 28)
    assert order.items
    for item in order.items:
        assert item.order_id == 8
        assert item.product is data.products[item.product_id]


def test_unshipped_order_has_no_delivery_date():
    assert load_data().orders[9].estimated_delivery is None


def test_normalizers():
    assert normalize_text("Violão  Cedr") == "violao cedr"
    assert normalize_phone("(67) 99812-3456") == "67998123456"
    assert normalize_email("  Lucas.Mendes@JMAIL.com ") == "lucas.mendes@jmail.com"
