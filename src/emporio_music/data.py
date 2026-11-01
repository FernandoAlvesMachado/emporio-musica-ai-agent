"""Validate the supplied CSV files and import an atomic SQLite snapshot."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path

from .text import normalize_text


class DataValidationError(ValueError):
    """A source file cannot safely be imported."""


@dataclass(frozen=True)
class ImportReport:
    counts: dict[str, int]
    warnings: tuple[str, ...]


HEADERS = {
    "categories": ("category_id", "name", "description"),
    "products": (
        "product_id", "price_brl", "name", "category_id", "description",
        "stock_quantity", "status", "specs", "created_at",
    ),
    "promotions": (
        "promotion_id", "product_id", "discount_percent", "description", "is_active",
    ),
    "customers": ("customer_id", "name", "phone", "email", "city"),
    "orders": (
        "order_id", "customer_id", "order_date", "status", "total_brl",
        "payment_method", "tracking_code", "estimated_delivery", "notes",
    ),
    "order_items": ("order_id", "quantity", "product_id"),
}

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY CHECK(category_id > 0),
        name TEXT NOT NULL, description TEXT)""",
    """CREATE TABLE IF NOT EXISTS products (
        product_id INTEGER PRIMARY KEY CHECK(product_id > 0),
        price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
        name TEXT NOT NULL, category_id INTEGER NOT NULL REFERENCES categories(category_id),
        description TEXT, stock_quantity INTEGER NOT NULL CHECK(stock_quantity >= 0),
        status TEXT NOT NULL CHECK(status IN ('active','discontinued','coming_soon')),
        specs_json TEXT, created_at TEXT NOT NULL, search_name TEXT NOT NULL)""",
    """CREATE TABLE IF NOT EXISTS promotions (
        promotion_id INTEGER PRIMARY KEY CHECK(promotion_id > 0),
        product_id INTEGER NOT NULL REFERENCES products(product_id),
        discount_percent INTEGER NOT NULL CHECK(discount_percent BETWEEN 1 AND 100),
        description TEXT, is_active INTEGER NOT NULL CHECK(is_active IN (0,1)))""",
    """CREATE TABLE IF NOT EXISTS customers (
        customer_id INTEGER PRIMARY KEY CHECK(customer_id > 0),
        name TEXT NOT NULL, phone TEXT, email TEXT, city TEXT)""",
    """CREATE TABLE IF NOT EXISTS orders (
        order_id INTEGER PRIMARY KEY CHECK(order_id > 0),
        customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
        order_date TEXT NOT NULL, status TEXT NOT NULL,
        total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
        payment_method TEXT NOT NULL, tracking_code TEXT,
        estimated_delivery TEXT, notes TEXT)""",
    """CREATE TABLE IF NOT EXISTS order_items (
        order_id INTEGER NOT NULL REFERENCES orders(order_id),
        quantity INTEGER NOT NULL CHECK(quantity > 0),
        product_id INTEGER NOT NULL REFERENCES products(product_id),
        PRIMARY KEY(order_id, product_id))""",
    "CREATE INDEX IF NOT EXISTS products_category ON products(category_id)",
    "CREATE INDEX IF NOT EXISTS products_price ON products(price_cents)",
    "CREATE INDEX IF NOT EXISTS promotions_product ON promotions(product_id, is_active)",
    "CREATE INDEX IF NOT EXISTS orders_customer ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS order_items_product ON order_items(product_id)",
)


def _integer(value: str, *, minimum: int = 1, maximum: int = 2**63 - 1) -> int:
    if not re.fullmatch(r"[0-9]+", value):
        raise ValueError("expected an integer")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"expected an integer between {minimum} and {maximum}")
    return number


def parse_money_to_cents(value: str) -> int:
    """Parse source-format BRL exactly, rejecting ambiguous or invalid amounts."""
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]{1,2})?", value):
        raise ValueError("expected nonnegative BRL with a decimal point and at most two decimals")
    try:
        amount = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("invalid monetary amount") from exc
    if amount > Decimal("92233720368547758.07"):
        raise ValueError("monetary amount exceeds SQLite integer capacity")
    with localcontext() as context:
        context.prec = 28
        return int(amount * 100)


def _iso_date(value: str) -> str:
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise ValueError("expected an ISO date in YYYY-MM-DD format")
    try:
        return date.fromisoformat(value).isoformat()
    except ValueError as exc:
        raise ValueError("invalid calendar date") from exc


def _required(value: str) -> str:
    if not value:
        raise ValueError("required value is missing")
    return value


def _specs(value: str) -> str | None:
    if not value:
        return None
    try:
        def reject_constant(_: str) -> None:
            raise ValueError("expected finite JSON values")

        result = json.loads(value, parse_constant=reject_constant)
    except json.JSONDecodeError as exc:
        raise ValueError("expected a JSON object") from exc
    if not isinstance(result, dict):
        raise ValueError("expected a JSON object")
    return json.dumps(result, ensure_ascii=False, allow_nan=False)


def _status(value: str) -> str:
    if value not in {"active", "discontinued", "coming_soon"}:
        raise ValueError("expected active, discontinued, or coming_soon")
    return value


def _boolean(value: str) -> int:
    if value not in {"0", "1"}:
        raise ValueError("expected promotion flag 0 or 1")
    return int(value)


def _parse_row(table: str, row: dict[str, str], filename: str, line: int) -> dict:
    parsed = {}
    for field, value in row.items():
        try:
            target = field
            if field.endswith("_id"):
                result = _integer(value)
            elif field in {"price_brl", "total_brl"}:
                target = field.replace("_brl", "_cents")
                result = parse_money_to_cents(value)
            elif field == "stock_quantity":
                result = _integer(value, minimum=0)
            elif field == "quantity":
                result = _integer(value)
            elif field == "discount_percent":
                result = _integer(value, maximum=100)
            elif field == "is_active":
                result = _boolean(value)
            elif field in {"created_at", "order_date"}:
                result = _iso_date(value)
            elif field == "estimated_delivery":
                result = _iso_date(value) if value else None
            elif field == "specs":
                target = "specs_json"
                result = _specs(value)
            elif field == "status" and table == "products":
                result = _status(value)
            elif field in {"name", "status", "payment_method"}:
                result = _required(value)
            else:
                result = value or None
        except (ValueError, OverflowError) as exc:
            raise DataValidationError(f"{filename}: row {line}, field {field}: {exc}") from exc
        parsed[target] = result
    if table == "products":
        parsed["search_name"] = normalize_text(parsed["name"])
    return parsed


def _load_table(raw_dir: Path, table: str) -> tuple[list[dict], list[int], str]:
    candidates = sorted(
        path for path in raw_dir.glob("*.csv")
        if path.stem == table or path.stem.endswith(f" - {table}")
    )
    if len(candidates) != 1:
        raise DataValidationError(
            f"{table}: expected exactly one {table}.csv or '* - {table}.csv' in {raw_dir}; "
            f"found {len(candidates)}"
        )
    path = candidates[0]
    rows, lines, seen = [], [], set()
    try:
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream, strict=True)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)) or set(headers) != set(HEADERS[table]):
                raise DataValidationError(
                    f"{path.name}: expected columns {', '.join(HEADERS[table])}"
                )
            for row in reader:
                line = reader.line_num
                if None in row or any(value is None for value in row.values()):
                    raise DataValidationError(f"{path.name}: row {line}: incorrect column count")
                parsed = _parse_row(table, {key: value.strip() for key, value in row.items()}, path.name, line)
                identifier = "category_id" if table == "categories" else f"{table[:-1]}_id"
                key_fields = ("order_id", "product_id") if table == "order_items" else (identifier,)
                key = tuple(parsed[field] for field in key_fields)
                if key in seen:
                    raise DataValidationError(f"{path.name}: row {line}: duplicate primary key")
                seen.add(key)
                rows.append(parsed)
                lines.append(line)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataValidationError(f"{path.name}: cannot read valid UTF-8 CSV ({type(exc).__name__})") from exc
    return rows, lines, path.name


def import_data(raw_dir: Path, database_path: Path) -> ImportReport:
    """Import all six files as one validated snapshot; leave existing data on failure."""
    raw_dir, database_path = Path(raw_dir), Path(database_path)
    if database_path.resolve().suffix.lower() in {".csv", ".pdf"}:
        raise DataValidationError("Database path must not point to a CSV or PDF source file; use a separate .sqlite3 path.")
    tables, locations = {}, {}
    for table in HEADERS:
        rows, lines, filename = _load_table(raw_dir, table)
        tables[table] = rows
        locations[table] = (lines, filename)

    relationships = (
        ("products", "category_id", "categories"),
        ("promotions", "product_id", "products"),
        ("orders", "customer_id", "customers"),
        ("order_items", "order_id", "orders"),
        ("order_items", "product_id", "products"),
    )
    for child, field, parent in relationships:
        parent_ids = {row[field] for row in tables[parent]}
        lines, filename = locations[child]
        for row, line in zip(tables[child], lines):
            if row[field] not in parent_ids:
                raise DataValidationError(f"{filename}: row {line}, field {field}: referenced {parent} row is missing")

    warnings = []
    for product in tables["products"]:
        if product["status"] != "active" and product["stock_quantity"] > 0:
            warnings.append(f"Product {product['product_id']} has stock but status {product['status']}; unavailable for sale.")
        elif product["status"] == "active" and product["stock_quantity"] == 0:
            warnings.append(f"Product {product['product_id']} is active but out of stock.")
    active_offers = Counter(row["product_id"] for row in tables["promotions"] if row["is_active"])
    for product_id, count in sorted(active_offers.items()):
        if count > 1:
            warnings.append(f"Product {product_id} has multiple active promotions; no single promotional price can be inferred.")
    missing_delivery = sum(not row["estimated_delivery"] for row in tables["orders"])
    missing_tracking = sum(not row["tracking_code"] for row in tables["orders"])
    if missing_delivery or missing_tracking:
        warnings.append(f"Optional order fields missing: tracking_code={missing_tracking}, estimated_delivery={missing_delivery}.")
    warnings.append("Promotions have no validity dates; is_active reflects the supplied snapshot only.")

    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = None
    try:
        connection = sqlite3.connect(database_path)
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("BEGIN IMMEDIATE")
        for statement in SCHEMA:
            connection.execute(statement)
        for table in reversed(HEADERS):
            connection.execute(f"DELETE FROM {table}")
        for table, rows in tables.items():
            if not rows:
                continue
            columns = tuple(rows[0])
            placeholders = ", ".join("?" for _ in columns)
            connection.executemany(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                [tuple(row[column] for column in columns) for row in rows],
            )
        connection.commit()
    except sqlite3.Error as exc:
        if connection is not None:
            connection.rollback()
        raise DataValidationError(
            f"Cannot replace SQLite snapshot ({type(exc).__name__}); "
            "check the database path, write permissions, and existing schema."
        ) from exc
    except BaseException:
        if connection is not None:
            connection.rollback()
        raise
    finally:
        if connection is not None:
            connection.close()
    return ImportReport({table: len(rows) for table, rows in tables.items()}, tuple(warnings))
