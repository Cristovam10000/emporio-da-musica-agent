"""Store business rules from data/políticas_da_loja.pdf (v2.1). Pure functions, no I/O."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

import holidays

TZ = ZoneInfo("America/Campo_Grande")
CENTS = Decimal("0.01")

PIX_DISCOUNT = Decimal("0.05")  # PDF 3 (table) and 6.2
SPLIT_PAYMENT_THRESHOLD = Decimal("2000.00")  # PDF 3.1: "acima de R$ 2.000,00"
# (max installments in band, minimum installment) - PDF 3.1; the R$50 for 1-3x is assumption P3
INSTALLMENT_BANDS = ((3, Decimal("50")), (6, Decimal("80")), (12, Decimal("100")))
# weekday() -> (opens, closes); Sunday absent = closed. PDF 2.
OPENING_HOURS = {d: (time(9), time(18)) for d in range(5)} | {5: (time(9), time(13))}

_BR_MS_HOLIDAYS = holidays.country_holidays("BR", subdiv="MS")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def effective_price(list_price, promo_percent=None) -> Decimal:
    """Promo price when a promo is active, else the list price."""
    price = Decimal(str(list_price))
    if promo_percent:
        price = price * (100 - Decimal(str(promo_percent))) / 100
    return _money(price)


def pix_price(list_price, promo_percent=None) -> Decimal | None:
    """List price minus the PIX discount; None when a promo is active (not cumulative, PDF 6.2)."""
    if promo_percent:
        return None
    return _money(Decimal(str(list_price)) * (1 - PIX_DISCOUNT))


def max_installments(amount) -> tuple[int, Decimal]:
    """Largest interest-free n <= 12 whose exact share amount/n meets the band minimum.

    The check uses the unrounded share, so 799.99 is 7x, not 8x (8 x 99.99875 < 100).
    """
    amount = Decimal(str(amount))
    for n in range(12, 1, -1):
        minimum = next(m for top, m in INSTALLMENT_BANDS if n <= top)
        if amount / n >= minimum:
            return n, _money(amount / n)
    return 1, _money(amount)


def allows_split_payment(amount) -> bool:
    """Combining payment methods is allowed only strictly above R$2,000 (PDF 3.1)."""
    return Decimal(str(amount)) > SPLIT_PAYMENT_THRESHOLD


@dataclass(frozen=True)
class StoreStatus:
    is_open: bool
    next_opening: datetime | None  # set only when closed
    closes_at: datetime | None  # set only when open


def holiday_name(day: date) -> str | None:
    """National + MS holidays, plus Campo Grande's anniversary (Aug 26); None on other days.

    shortcut: other municipal holidays and optional days (e.g. Carnival) are not covered.
    """
    if (day.month, day.day) == (8, 26):
        return "Campo Grande anniversary"
    return _BR_MS_HOLIDAYS.get(day)


def _hours(day: date):
    return None if holiday_name(day) else OPENING_HOURS.get(day.weekday())


def store_status(now: datetime) -> StoreStatus:
    """Open/closed at `now`. Naive datetimes are taken as Campo Grande local time.

    Aware datetimes are converted to Campo Grande; returned datetimes are Campo Grande-aware.
    The store is open from the opening minute up to, but not including, the closing minute.
    """
    now = now.replace(tzinfo=TZ) if now.tzinfo is None else now.astimezone(TZ)
    hours = _hours(now.date())
    if hours and hours[0] <= now.time() < hours[1]:
        return StoreStatus(True, None, datetime.combine(now.date(), hours[1], TZ))
    day = now.date()
    if not (hours and now.time() < hours[0]):
        day += timedelta(days=1)
        while not _hours(day):
            day += timedelta(days=1)
    return StoreStatus(False, datetime.combine(day, _hours(day)[0], TZ), None)


@dataclass(frozen=True)
class Window:
    deadline: date
    still_open: bool


@dataclass(frozen=True)
class ReturnWindows:
    regret: Window  # PDF 4.1, online purchases: 7 calendar days from receipt
    preference_exchange: Window  # PDF 4.3: 7 days, from receipt (assumption P6)
    defect_exchange: Window | None  # PDF 4.2: 30 days from purchase; None without purchased_on
    legal_warranty: Window  # PDF 8.1: 90 days from receipt


def return_windows(received_on: date, today: date, purchased_on: date | None = None) -> ReturnWindows:
    """Deadline = start date + N days, and the deadline day itself is still inside the window.

    Received Nov 1 -> 7-day deadline Nov 8: open on Nov 8, closed on Nov 9.
    """

    def window(start: date, days: int) -> Window:
        deadline = start + timedelta(days=days)
        return Window(deadline, today <= deadline)

    return ReturnWindows(
        regret=window(received_on, 7),
        preference_exchange=window(received_on, 7),
        defect_exchange=window(purchased_on, 30) if purchased_on else None,
        legal_warranty=window(received_on, 90),
    )
