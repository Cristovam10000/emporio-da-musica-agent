from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from emporio.rules import (
    TZ,
    allows_split_payment,
    effective_price,
    max_installments,
    pix_price,
    return_windows,
    store_status,
)

D = Decimal


def cg(*args):
    return datetime(*args, tzinfo=TZ)


# --- prices ---

def test_pix_on_list_price():
    assert effective_price(D("2199.00")) == D("2199.00")
    assert pix_price(D("2199.00")) == D("2089.05")


def test_promo_price_and_no_pix_on_promo():
    assert effective_price(D("549.00"), 20) == D("439.20")
    assert pix_price(D("549.00"), 20) is None


# --- installments ---

@pytest.mark.parametrize(
    "amount, expected",
    [
        ("150", (3, D("50.00"))),
        ("240", (3, D("80.00"))),  # 4x would be 60 < 80
        ("320", (4, D("80.00"))),
        ("599", (6, D("99.83"))),  # 7x would be 85.57 < 100
        ("700", (7, D("100.00"))),
        ("1200", (12, D("100.00"))),
        ("1200.30", (12, D("100.03"))),  # 100.025 -> HALF_UP, not 100.02
        ("799.99", (7, D("114.28"))),  # 8x share 99.99875 is below 100
        ("100", (2, D("50.00"))),
        ("99.99", (1, D("99.99"))),
        ("30", (1, D("30.00"))),
    ],
)
def test_max_installments(amount, expected):
    assert max_installments(D(amount)) == expected


def test_split_payment_strictly_above_2000():
    assert not allows_split_payment(D("2000.00"))
    assert allows_split_payment(D("2000.01"))


# --- store hours ---

def test_sunday_night_reopens_tuesday_after_finados():
    s = store_status(cg(2026, 11, 1, 21, 0))
    assert not s.is_open and s.closes_at is None
    assert s.next_opening == cg(2026, 11, 3, 9, 0)


def test_weekday_inside_hours_is_open():
    s = store_status(cg(2026, 11, 4, 10, 30))
    assert s.is_open and s.next_opening is None
    assert s.closes_at == cg(2026, 11, 4, 18, 0)


def test_weekday_before_opening_opens_same_day_and_closing_minute_is_closed():
    assert store_status(cg(2026, 11, 4, 8, 0)).next_opening == cg(2026, 11, 4, 9, 0)
    assert store_status(cg(2026, 11, 4, 18, 0)).next_opening == cg(2026, 11, 5, 9, 0)


def test_saturday_hours():
    assert store_status(cg(2026, 11, 7, 12, 59)).closes_at == cg(2026, 11, 7, 13, 0)
    after = store_status(cg(2026, 11, 7, 13, 0))
    assert not after.is_open and after.next_opening == cg(2026, 11, 9, 9, 0)


def test_campo_grande_anniversary_is_closed():
    s = store_status(cg(2026, 8, 26, 10, 0))  # Wednesday
    assert not s.is_open and s.next_opening == cg(2026, 8, 27, 9, 0)


def test_naive_is_local_and_aware_is_converted():
    assert store_status(datetime(2026, 11, 4, 10, 0)).is_open
    # 13:30 UTC = 09:30 in Campo Grande (UTC-4)
    assert store_status(datetime(2026, 11, 4, 13, 30, tzinfo=timezone.utc)).is_open


# --- return windows ---

def test_seven_day_windows_include_day_seven():
    received = date(2026, 11, 1)
    day7 = return_windows(received, date(2026, 11, 8))
    day8 = return_windows(received, date(2026, 11, 9))
    assert day7.regret.deadline == date(2026, 11, 8)
    assert day7.regret.still_open and day7.preference_exchange.still_open
    assert not day8.regret.still_open and not day8.preference_exchange.still_open
    assert day7.defect_exchange is None


def test_defect_window_counts_from_purchase():
    w = return_windows(date(2026, 10, 10), date(2026, 10, 31), purchased_on=date(2026, 10, 1))
    assert w.defect_exchange.deadline == date(2026, 10, 31) and w.defect_exchange.still_open
    w = return_windows(date(2026, 10, 10), date(2026, 11, 1), purchased_on=date(2026, 10, 1))
    assert not w.defect_exchange.still_open


def test_legal_warranty_90_days_from_receipt():
    received = date(2026, 8, 1)
    w =return_windows(received, date(2026, 10, 30))
    assert w.legal_warranty.deadline == date(2026, 10, 30) and w.legal_warranty.still_open
    assert not return_windows(received, date(2026, 10, 31)).legal_warranty.still_open
