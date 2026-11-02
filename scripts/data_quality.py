"""Print a Markdown "Data quality findings" section computed from the CSVs (plan D1-D10).

Usage: python scripts/data_quality.py
"""

import sys
from collections import defaultdict
from datetime import date
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from emporio import tools  # noqa: E402
from emporio.data import load_data, normalize_email  # noqa: E402
from emporio.rules import max_installments  # noqa: E402

OPEN_STATUSES = ("pending", "confirmed", "shipped")


def ids(values) -> str:
    return ", ".join(str(v) for v in values) or "none"


def findings(today: date) -> list[tuple[str, str]]:
    data = load_data()
    products, orders = data.products.values(), list(data.orders.values())
    sold = {i.product_id for o in orders for i in o.items}
    out = []

    dates = [o.order_date for o in orders]
    late = [o for o in orders if o.status in OPEN_STATUSES and o.estimated_delivery and o.estimated_delivery < today]
    out.append(("D1 Order dates vs today",
                f"Orders span {min(dates)} to {max(dates)}; today is {today}. "
                f"{len(late)} open orders (pending/confirmed/shipped) have an estimated delivery in the past: "
                + "; ".join(f"order {o.order_id} ({o.status}, due {o.estimated_delivery})" for o in late)))

    out.append(("D2 Discontinued with stock",
                "; ".join(f"product {p.product_id} (stock {p.stock_quantity})"
                          for p in products if p.status == "discontinued" and p.stock_quantity > 0) or "none"))

    out.append(("D3 Coming soon with stock or already sold",
                "; ".join(f"product {p.product_id} (stock {p.stock_quantity}, in orders "
                          f"{ids(o.order_id for o in orders for i in o.items if i.product_id == p.product_id)})"
                          for p in products if p.status == "coming_soon"
                          and (p.stock_quantity > 0 or p.product_id in sold)) or "none"))

    out.append(("D4 Active with stock 0",
                "products " + ids(p.product_id for p in products if p.status == "active" and p.stock_quantity == 0)))

    diffs = []
    for o in orders:
        current = sum(i.product.price_brl * i.quantity for i in o.items)
        if current != o.total_brl:
            diffs.append(f"order {o.order_id} (total {o.total_brl}, current list prices {current})")
    out.append(("D5 Order total != sum of current item list prices",
                "Unexplained difference (order_items has no historical price): " + ("; ".join(diffs) or "none")))

    bad = []
    for o in orders:
        if o.payment_method.startswith("credit_"):
            n = int(o.payment_method.removeprefix("credit_").removesuffix("x"))
            limit = max_installments(o.total_brl)[0]
            if n > limit:
                bad.append(f"order {o.order_id} ({n}x on {o.total_brl}, rules allow {limit}x)")
    out.append(("D6 Installments outside the rules", "; ".join(bad) or "none"))

    by_email = defaultdict(list)
    for c in data.customers.values():
        by_email[normalize_email(c.email)].append(c.customer_id)
    out.append(("D7 Duplicated customer e-mails",
                "; ".join(f"customers {ids(v)} share {e}" for e, v in by_email.items() if len(v) > 1) or "none"))

    inactive = defaultdict(list)
    for p in data.promotions:
        if not p.is_active:
            inactive[p.product_id].append(p.promotion_id)
    out.append(("D8 Promotions",
                f"Active (product: -%): {', '.join(f'{pid}: -{p.discount_percent}%' for pid, p in data.active_promotions.items())}. "
                f"Products with several inactive promotions: "
                + ("; ".join(f"product {pid} (promotions {ids(v)})" for pid, v in inactive.items() if len(v) > 1) or "none")
                + ". Promotions have no dates, only is_active."))

    keys = defaultdict(set)
    for p in products:
        keys[data.categories[p.category_id].name] |= set(p.specs)
    common = set.intersection(*keys.values())
    out.append(("D9 Spec keys vary by category",
                "; ".join(f"{cat}: {', '.join(sorted(k - common))}" for cat, k in keys.items())
                + f". Keys in every category: {', '.join(sorted(common)) or 'none'}"))

    order = [p.product_id for p in products]
    misplaced = [pid for prev, pid in zip(order, order[1:]) if pid < prev]
    out.append(("D10 Product ids out of order",
                f"File order breaks before product {ids(misplaced)}" if misplaced else "ids are sorted"))
    return out


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    print("## Data quality findings\n")
    for title, text in findings(tools.now().date()):
        print(f"- **{title}:** {text}")


if __name__ == "__main__":
    main()
