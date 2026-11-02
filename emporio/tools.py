"""The five LangChain tools the agent can call.

Every tool returns a JSON-serializable dict: money as "R$ 2.199,00", dates as ISO strings.
Expected failures (not found, contact mismatch, empty result) are returned as data, never
raised: an exception inside a tool crashes the agent loop.
"""

import difflib
import json
import re
from datetime import date, datetime
from decimal import ROUND_DOWN, Decimal
from functools import cache
from pathlib import Path
from typing import Literal

from langchain.tools import tool
from pydantic import BaseModel, Field, field_validator

from emporio.data import Product, load_data, normalize_email, normalize_phone, normalize_text
from emporio.rules import TZ, allows_split_payment, effective_price, max_installments, pix_price, return_windows

ROOT = Path(__file__).resolve().parent.parent
POLICIES_PATH = ROOT / "knowledge" / "policies.md"
TICKETS_PATH = ROOT / "tickets.jsonl"  # module attribute so tests can point it elsewhere

# category_id -> slug used in tool arguments and results
CATEGORY_SLUGS = {
    1: "guitarras",
    2: "baixos",
    3: "baterias_percussao",
    4: "teclados_pianos",
    5: "violoes",
    6: "sopro_madeiras",
    7: "sopro_metais",
    8: "cordas_orquestrais",
    9: "ukuleles",
}
CategorySlug = Literal[
    "guitarras", "baixos", "baterias_percussao", "teclados_pianos", "violoes",
    "sopro_madeiras", "sopro_metais", "cordas_orquestrais", "ukuleles",
]
PolicyTopic = Literal[
    "contato_endereco", "horario", "pagamento_parcelamento", "trocas_devolucoes",
    "frete_entrega", "promocoes", "garantia", "privacidade", "sobre_loja",
]

# --- clock -------------------------------------------------------------------------------

_now: datetime | None = None


def set_now(dt: datetime | None) -> None:
    """Freeze the tools' clock (naive = Campo Grande time); None goes back to real time."""
    global _now
    _now = dt if dt is None or dt.tzinfo else dt.replace(tzinfo=TZ)


def now() -> datetime:
    return (_now or datetime.now(TZ)).astimezone(TZ)


# --- shared helpers ----------------------------------------------------------------------


def brl(value: Decimal) -> str:
    """Decimal('2199') -> 'R$ 2.199,00'."""
    return "R$ " + f"{value:,.2f}".translate(str.maketrans(",.", ".,"))


def installments_view(price: Decimal) -> dict:
    """Interest-free plan; "last_value" only when the cents make the last installment differ.

    Shares are truncated to the cent and the remainder goes to the last one, so the installments
    add up to the price and none falls below the tier minimum (rounding up could push the last
    one under it: 12x of 1200.06 would end with R$ 99,95).
    """
    n, _ = max_installments(price)
    value = (price / n).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    last = price - value * (n - 1)
    plan = {"max": n, "value": brl(value)}
    if last != value:
        plan["last_value"] = brl(last)
    return plan


def _availability(p: Product) -> str:
    if p.status == "active":
        return "available" if p.stock_quantity > 0 else "temporarily_unavailable"
    return p.status  # "discontinued" or "coming_soon"


def product_view(p: Product) -> dict:
    promo = load_data().active_promotions.get(p.product_id)
    percent = promo.discount_percent if promo else None
    price = effective_price(p.price_brl, percent)
    pix = pix_price(p.price_brl, percent)
    availability = _availability(p)
    return {
        "product_id": p.product_id,
        "name": p.name,
        "category": CATEGORY_SLUGS[p.category_id],
        "list_price": brl(p.price_brl),
        "promotion": {"percent": percent, "price": brl(price), "original_price": brl(p.price_brl)} if promo else None,
        "pix_price": brl(pix) if pix else None,
        "installments": installments_view(price),
        "split_payment_allowed": allows_split_payment(price),
        "availability": availability,
        "low_stock": availability == "available" and p.stock_quantity <= 2,
        "specs": p.specs,
    }


def _current_price(p: Product) -> Decimal:
    promo = load_data().active_promotions.get(p.product_id)
    return effective_price(p.price_brl, promo.discount_percent if promo else None)


# --- find_product ------------------------------------------------------------------------

MIN_TOKEN_SIMILARITY = 0.75  # below this a token pair counts as no match ("gd20" vs "gc1ce")
MIN_SCORE = 0.5  # a product must match at least half of the query to be a candidate
PLAUSIBLE_MARGIN = 0.15  # candidates this close to the best one are equally plausible


def _tokens(text: str) -> list[str]:
    # Letter/digit runs, so "gd20", "gd-20" and "gd 20" all become ["gd", "20"].
    return re.findall(r"[a-z]+|[0-9]+", normalize_text(text))


@cache
def _search_tokens(product_id: int) -> tuple[frozenset[str], frozenset[str]]:
    """(name tokens, all tokens: name + category + description + specs)."""
    p = load_data().products[product_id]
    category = load_data().categories[p.category_id]
    specs = " ".join(str(v) for v in p.specs.values())
    name = frozenset(_tokens(p.name))
    return name, name | frozenset(_tokens(f"{category.name} {p.description} {specs}"))


def _score(query_tokens: list[str], product_tokens: tuple[frozenset[str], frozenset[str]]) -> float:
    """Average, over the query tokens, of the best similarity to any product token."""
    name_tokens, all_tokens = product_tokens
    total = 0.0
    for q in query_tokens:
        # Short tokens are model-code fragments ("d", "28", "e"); matching them in prose
        # would let the Portuguese "e" (and) turn "d-28" into "d-28e".
        pool = name_tokens if len(q) <= 2 else all_tokens
        best = max(difflib.SequenceMatcher(None, q, t).ratio() for t in pool)
        total += best if best >= MIN_TOKEN_SIMILARITY else 0
    return total / len(query_tokens)


class FindProductArgs(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=100,
        description="Product the customer named, as they wrote it (brand, model, or both), e.g. 'takamine gd20'.",
    )


@tool(args_schema=FindProductArgs)
def find_product(name: str) -> dict:
    """Look up a SPECIFIC product the customer names (brand and/or model), in any status.

    Use it for price, availability, specs or promotion questions about a named product.
    Returns up to 5 matches, best first. When "ambiguous" is true (several candidates, or a
    model number the closest product does not have, explained in "note"), ask the customer
    to confirm the product before giving a price. For browsing by category or budget, use
    list_products instead.
    """
    query_tokens = _tokens(name)
    if not query_tokens:
        return {"query": name, "ambiguous": False, "matches": []}
    scored = sorted(
        ((_score(query_tokens, _search_tokens(pid)), p) for pid, p in load_data().products.items()),
        key=lambda pair: pair[0],
        reverse=True,
    )
    best = scored[0][0]
    plausible = [(s, p) for s, p in scored if s >= MIN_SCORE and s >= best - PLAUSIBLE_MARGIN][:5]
    # Brand and prefix can outscore a wrong number ("gd99" -> GD20): a model number must be in the name.
    unknown_number = bool(plausible) and any(
        t.isdigit() and t not in _search_tokens(plausible[0][1].product_id)[0] for t in query_tokens
    )
    result = {
        "query": name,
        "ambiguous": len(plausible) > 1 or unknown_number,
        "matches": [{**product_view(p), "score": round(s, 2)} for s, p in plausible],
    }
    if unknown_number:
        result["note"] = (
            f"No exact model match for '{name}'; closest products shown - ask the customer to "
            "confirm before quoting a price."
        )
    return result


# --- list_products -----------------------------------------------------------------------


class ListProductsArgs(BaseModel):
    category: CategorySlug | None = Field(
        None,
        description=(
            "guitarras = electric guitars; baixos = bass guitars; baterias_percussao = drums and "
            "percussion; teclados_pianos = keyboards, digital pianos, synths, MIDI controllers; "
            "violoes = acoustic and classical guitars (violão); sopro_madeiras = woodwinds (flute, "
            "clarinet, sax); sopro_metais = brass (trumpet, trombone); cordas_orquestrais = "
            "orchestral strings (violin, cello); ukuleles = ukuleles."
        ),
    )
    max_price: Decimal | None = Field(None, ge=0, description="Highest current price in BRL, e.g. 1000.")
    min_price: Decimal | None = Field(None, ge=0, description="Lowest current price in BRL.")
    strings: Literal["nylon", "steel"] | None = Field(
        None, description="String type, for acoustic guitars: nylon (classical) or steel (aço, folk)."
    )
    electronics: bool | None = Field(
        None, description="True = with pickup/electronics (eletroacústico); False = purely acoustic."
    )
    limit: int = Field(8, ge=1, le=20, description="Maximum number of products to return.")


@tool(args_schema=ListProductsArgs)
def list_products(
    category: str | None = None,
    max_price: Decimal | None = None,
    min_price: Decimal | None = None,
    strings: str | None = None,
    electronics: bool | None = None,
    limit: int = 8,
) -> dict:
    """Browse products the customer can buy now, filtered by category, budget and specs.

    Use it for open questions like "acoustic guitars up to R$1000" or "what ukuleles do you
    have?". Only purchasable items are listed (active and in stock), cheapest first. Prices
    are filtered by the current price (promotion price when one is active). For a product the
    customer names, use find_product instead.
    """
    data = load_data()
    found = []
    for p in data.products.values():
        price = _current_price(p)
        if (
            p.status == "active"
            and p.stock_quantity > 0
            and (category is None or CATEGORY_SLUGS[p.category_id] == category)
            and (max_price is None or price <= max_price)
            and (min_price is None or price >= min_price)
            and (strings is None or p.specs.get("strings") == strings)
            and (electronics is None or p.specs.get("electronics") == ("yes" if electronics else "no"))
        ):
            found.append((price, p))
    found.sort(key=lambda pair: pair[0])
    result = {"total_matches": len(found), "products": [product_view(p) for _, p in found[:limit]]}
    if category and not any(CATEGORY_SLUGS[p.category_id] == category for p in data.products.values()):
        result["note"] = f"There are no products in the category '{category}' in the system right now."
    return result


# --- get_order_status --------------------------------------------------------------------

ORDER_NOT_FOUND = {"found": False, "message": "Order not found or the contact does not match."}


def _contact_matches(contact: str, email: str, phone: str) -> bool:
    if "@" in contact:
        return normalize_email(contact) == normalize_email(email)
    digits = normalize_phone(contact)
    if len(digits) > 11 and digits.startswith("55"):  # Brazilian numbers have 10-11 digits
        digits = digits[2:]
    return bool(digits) and digits == normalize_phone(phone)


class GetOrderStatusArgs(BaseModel):
    order_id: int = Field(ge=1, description="Order number given by the customer.")
    contact: str = Field(
        min_length=3, max_length=100, description="E-mail or phone of the buyer, as the customer gave it."
    )
    received_on: date | None = Field(
        None,
        description=(
            "Date the CUSTOMER says they received the item (ISO, e.g. 2026-10-28). Only for "
            "return/exchange/warranty questions; never guess it."
        ),
    )

    @field_validator("received_on")
    @classmethod
    def not_in_future(cls, value: date | None) -> date | None:
        if value and value > now().date():
            raise ValueError("received_on cannot be in the future")
        return value


@tool(args_schema=GetOrderStatusArgs)
def get_order_status(order_id: int, contact: str, received_on: date | None = None) -> dict:
    """Check an order's status, items, total, tracking and delay, after verifying the buyer.

    Use it when the customer asks about an existing order. Needs the order number AND the
    buyer's e-mail or phone; ask for both if missing. Pass received_on only when the customer
    told you when they received the item; the result then includes the return/exchange and
    warranty deadlines, or "received_on_error" when that date is before the order date.
    """
    data = load_data()
    order = data.orders.get(order_id)
    customer = data.customers.get(order.customer_id) if order else None
    if not customer or not _contact_matches(contact, customer.email, customer.phone):
        return dict(ORDER_NOT_FOUND)  # same answer for both cases: never reveal that the order exists

    today = now().date()
    result = {
        "found": True,
        "order_id": order.order_id,
        "customer_first_name": customer.name.split()[0],
        "status": order.status,
        "cancellation_reason": order.notes if order.status == "cancelled" else None,
        "order_date": order.order_date.isoformat(),
        "items": [{"name": i.product.name, "quantity": i.quantity} for i in order.items],
        "total": brl(order.total_brl),
        "payment_method": order.payment_method,
        "tracking_code": order.tracking_code or None,
        "estimated_delivery": order.estimated_delivery.isoformat() if order.estimated_delivery else None,
        "delayed": order.status not in ("delivered", "cancelled")
        and order.estimated_delivery is not None
        and order.estimated_delivery < today,
    }
    # Checked only after the contact matches, so a wrong contact still learns nothing.
    if received_on and received_on < order.order_date:
        result["received_on_error"] = (
            f"received_on {received_on.isoformat()} is before the order date {order.order_date.isoformat()}; "
            "ask the customer to check the date they received the item."
        )
    elif received_on:
        windows = return_windows(received_on, today, purchased_on=order.order_date)
        result["days_since_receipt"] = (today - received_on).days
        result["return_windows"] = {
            name: {"deadline": w.deadline.isoformat(), "still_open": w.still_open}
            for name, w in vars(windows).items()
            if w is not None
        }
    return result


# --- get_store_policy --------------------------------------------------------------------


@cache
def _policy_sections() -> dict[str, str]:
    """'## topic' heading -> section body, from knowledge/policies.md."""
    text = POLICIES_PATH.read_text(encoding="utf-8")
    sections = {}
    for chunk in text.split("\n## ")[1:]:
        topic, _, body = chunk.partition("\n")
        sections[topic.strip()] = body.strip()
    return sections


class GetStorePolicyArgs(BaseModel):
    topic: PolicyTopic = Field(
        description=(
            "contato_endereco = address, phone/WhatsApp, e-mail, company data; horario = opening "
            "hours; pagamento_parcelamento = payment methods, installments, PIX; trocas_devolucoes "
            "= returns, exchanges, regret period; frete_entrega = shipping, delivery, tracking; "
            "promocoes = promotions and discounts; garantia = legal and manufacturer warranty; "
            "privacidade = personal data (LGPD); sobre_loja = who the store is, mission, final provisions."
        )
    )


@tool(args_schema=GetStorePolicyArgs)
def get_store_policy(topic: str) -> dict:
    """Get the store's official policy text on one topic, with interpretation notes.

    Use it before answering any question about store rules: hours, address, payment and
    installments, returns and exchanges, shipping, promotions, warranty, privacy or the store
    itself. Answer from this text; do not rely on memory.
    """
    return {"topic": topic, "text": _policy_sections()[topic]}


# --- handoff_to_human --------------------------------------------------------------------


class HandoffArgs(BaseModel):
    reason: Literal["reclamacao", "pedido_atrasado", "devolucao_troca", "encomenda", "outro"] = Field(
        description=(
            "reclamacao = complaint; pedido_atrasado = late order; devolucao_troca = return or "
            "exchange; encomenda = special order of an item not in stock/catalog; outro = other."
        )
    )
    summary: str = Field(
        min_length=10, max_length=500, description="Short summary for the staff: what the customer needs."
    )
    order_id: int | None = Field(None, ge=1, description="Related order number, if any.")


@tool(args_schema=HandoffArgs)
def handoff_to_human(reason: str, summary: str, order_id: int | None = None) -> dict:
    """Open a ticket for the store staff and return its protocol number.

    Use it when the customer needs a person: complaints, late orders, returns or exchanges,
    special orders, or anything you cannot solve with the other tools. Tell the customer the
    protocol and that the team replies within 24 business hours.
    """
    timestamp = now()
    prefix = f"EMP-{timestamp:%Y%m%d}-"
    lines = TICKETS_PATH.read_text(encoding="utf-8").splitlines() if TICKETS_PATH.exists() else []
    # shortcut: sequence from a file scan, not safe for concurrent writers; use a DB sequence in production
    sequence = sum(json.loads(line)["protocol"].startswith(prefix) for line in lines if line.strip()) + 1
    protocol = f"{prefix}{sequence:03d}"
    ticket = {
        "protocol": protocol,
        "created_at": timestamp.isoformat(),
        "reason": reason,
        "summary": summary,
        "order_id": order_id,
    }
    with open(TICKETS_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(ticket, ensure_ascii=False) + "\n")
    return {"protocol": protocol, "simulated": True, "response_time": "up to 24 business hours"}


TOOLS = [find_product, list_products, get_order_status, get_store_policy, handoff_to_human]
