"""Load the store CSVs once into typed, indexed in-memory data.

Rows are kept as-is: data-quality issues are reported elsewhere, not fixed here.
"""

import csv
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from functools import cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CSV_PREFIX = "desafio_tecnico_ai_eng - "


@dataclass
class Category:
    category_id: int
    name: str
    description: str


@dataclass
class Product:
    product_id: int
    price_brl: Decimal
    name: str
    category_id: int
    description: str
    stock_quantity: int
    status: str
    specs: dict
    created_at: date


@dataclass
class Customer:
    customer_id: int
    name: str
    phone: str
    email: str
    city: str


@dataclass
class OrderItem:
    order_id: int
    quantity: int
    product_id: int
    product: Product


@dataclass
class Order:
    order_id: int
    customer_id: int
    order_date: date
    status: str
    total_brl: Decimal
    payment_method: str
    tracking_code: str  # "" when the order has not shipped
    estimated_delivery: date | None
    notes: str
    items: list[OrderItem] = field(default_factory=list)


@dataclass
class Promotion:
    promotion_id: int
    product_id: int
    discount_percent: int
    description: str
    is_active: bool


@dataclass
class StoreData:
    categories: dict[int, Category]
    products: dict[int, Product]
    customers: dict[int, Customer]
    orders: dict[int, Order]
    promotions: list[Promotion]
    active_promotions: dict[int, Promotion]  # by product_id


def _rows(data_dir: Path, name: str) -> list[dict[str, str]]:
    with open(data_dir / f"{CSV_PREFIX}{name}.csv", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _date(value: str) -> date | None:
    return date.fromisoformat(value) if value else None


@cache
def load_data(data_dir: Path = DATA_DIR) -> StoreData:
    categories = {
        int(r["category_id"]): Category(int(r["category_id"]), r["name"], r["description"])
        for r in _rows(data_dir, "categories")
    }
    products = {
        int(r["product_id"]): Product(
            product_id=int(r["product_id"]),
            price_brl=Decimal(r["price_brl"]),
            name=r["name"],
            category_id=int(r["category_id"]),
            description=r["description"],
            stock_quantity=int(r["stock_quantity"]),
            status=r["status"],
            specs=json.loads(r["specs"]),
            created_at=_date(r["created_at"]),
        )
        for r in _rows(data_dir, "products")
    }
    customers = {
        int(r["customer_id"]): Customer(
            int(r["customer_id"]), r["name"], r["phone"], r["email"], r["city"]
        )
        for r in _rows(data_dir, "customers")
    }
    orders = {
        int(r["order_id"]): Order(
            order_id=int(r["order_id"]),
            customer_id=int(r["customer_id"]),
            order_date=_date(r["order_date"]),
            status=r["status"],
            total_brl=Decimal(r["total_brl"]),
            payment_method=r["payment_method"],
            tracking_code=r["tracking_code"],
            estimated_delivery=_date(r["estimated_delivery"]),
            notes=r["notes"],
        )
        for r in _rows(data_dir, "orders")
    }
    for r in _rows(data_dir, "order_items"):
        product_id = int(r["product_id"])
        order = orders[int(r["order_id"])]
        order.items.append(
            OrderItem(order.order_id, int(r["quantity"]), product_id, products[product_id])
        )
    promotions = [
        Promotion(
            promotion_id=int(r["promotion_id"]),
            product_id=int(r["product_id"]),
            discount_percent=int(r["discount_percent"]),
            description=r["description"],
            is_active=r["is_active"] == "1",
        )
        for r in _rows(data_dir, "promotions")
    ]
    # shortcut: if a product ever had two active promotions, the last row wins.
    active_promotions = {p.product_id: p for p in promotions if p.is_active}
    return StoreData(categories, products, customers, orders, promotions, active_promotions)


def normalize_text(text: str) -> str:
    """Lowercase, strip accents and collapse whitespace: 'Violão  Cedr' -> 'violao cedr'."""
    decomposed = unicodedata.normalize("NFKD", text)
    no_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return " ".join(no_accents.lower().split())


def normalize_phone(phone: str) -> str:
    return re.sub(r"\D", "", phone)


def normalize_email(email: str) -> str:
    return email.strip().lower()
