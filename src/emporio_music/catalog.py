"""Parameterized catalog queries with explicit stock and promotion semantics."""

import json
import sqlite3
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path
from typing import Iterator

from emporio_music.data import parse_money_to_cents
from emporio_music.text import normalize_text


class CatalogError(ValueError):
    """The catalog snapshot is missing or unreadable."""


_CATALOG = """
WITH offers AS (
    SELECT product_id, COUNT(*) AS offer_count, MAX(discount_percent) AS discount
    FROM promotions WHERE is_active = 1 GROUP BY product_id
), catalog AS (
    SELECT p.*, c.name AS category_name,
           COALESCE(o.offer_count, 0) AS active_offer_count,
           (p.status = 'active' AND p.stock_quantity > 0) AS available,
           CASE WHEN o.offer_count = 1 AND p.status = 'active' AND p.stock_quantity > 0
                THEN (p.price_cents / 100) * (100 - o.discount)
                     + ((p.price_cents % 100) * (100 - o.discount) + 50) / 100
                ELSE p.price_cents END AS effective_price_cents
    FROM products AS p
    JOIN categories AS c ON c.category_id = p.category_id
    LEFT JOIN offers AS o ON o.product_id = p.product_id
)
"""


@contextmanager
def _connect(database_path: Path) -> Iterator[sqlite3.Connection]:
    if not database_path.is_file():
        raise CatalogError("Catalog database is missing. Run 'emporio load' first.")
    connection = None
    try:
        connection = sqlite3.connect(database_path.resolve().as_uri() + "?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        yield connection
    except sqlite3.Error as error:
        raise CatalogError("Catalog database is unreadable. Run 'emporio load' to rebuild it.") from error
    finally:
        if connection is not None:
            connection.close()


def _money(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _serialize(connection: sqlite3.Connection, row: sqlite3.Row) -> dict:
    promotions = [dict(offer) for offer in connection.execute(
        "SELECT promotion_id, discount_percent, description FROM promotions "
        "WHERE product_id = ? AND is_active = 1 ORDER BY promotion_id",
        (row["product_id"],),
    )]
    note = None
    if len(promotions) > 1:
        note = "Multiple active promotions: no discount applied; confirm the valid offer with staff."
    elif promotions and not row["available"]:
        note = "Product unavailable: no promotional price offered."
    return {
        "product_id": row["product_id"],
        "name": row["name"],
        "category_id": row["category_id"],
        "category_name": row["category_name"],
        "description": row["description"],
        "price_brl": _money(row["price_cents"]),
        "effective_price_brl": _money(row["effective_price_cents"]),
        "stock_quantity": row["stock_quantity"],
        "status": row["status"],
        "available": bool(row["available"]),
        "active_promotions": promotions,
        "promotion_note": note,
        "specs": json.loads(row["specs_json"]) if row["specs_json"] is not None else None,
        "created_at": row["created_at"],
    }


def search_products(
    database_path: Path,
    name: str = "",
    max_price: str | Decimal | None = None,
    available: bool | None = None,
    limit: int = 20,
) -> list[dict]:
    """Search literal name fragments; filter on the effective BRL price, inclusively."""
    if not isinstance(limit, int) or isinstance(limit, bool) or not 0 < limit <= 2**63 - 1:
        raise ValueError("Search limit must be a positive SQLite integer.")
    if available is not None and not isinstance(available, bool):
        raise ValueError("Availability must be true, false, or omitted.")
    conditions = []
    parameters: list = []
    if name.strip():
        escaped = normalize_text(name).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append("search_name LIKE ? ESCAPE '\\'")
        parameters.append(f"%{escaped}%")
    if max_price is not None:
        conditions.append("effective_price_cents <= ?")
        parameters.append(parse_money_to_cents(str(max_price)))
    if available is not None:
        conditions.append("available = ?")
        parameters.append(int(available))
    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    parameters.append(limit)
    with _connect(database_path) as connection:
        rows = connection.execute(
            _CATALOG + "SELECT * FROM catalog" + where
            + " ORDER BY effective_price_cents, product_id LIMIT ?", parameters,
        ).fetchall()
        return [_serialize(connection, row) for row in rows]


def get_product(database_path: Path, product_id: int) -> dict | None:
    """Return source-backed details, or None when an identifier does not exist."""
    if not isinstance(product_id, int) or isinstance(product_id, bool) or not 0 < product_id <= 2**63 - 1:
        raise ValueError("Product ID must be a positive SQLite integer.")
    with _connect(database_path) as connection:
        row = connection.execute(
            _CATALOG + "SELECT * FROM catalog WHERE product_id = ?", (product_id,),
        ).fetchone()
        return _serialize(connection, row) if row is not None else None
