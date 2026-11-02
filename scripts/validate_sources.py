"""Compare the application with independent CSV/PDF expectations, without an LLM."""

import csv
import json
import sqlite3
import tempfile
from collections import Counter
from contextlib import closing
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from pypdf import PdfReader

from emporio_music.catalog import get_product, search_products
from emporio_music.config import Settings
from emporio_music.data import import_data
from emporio_music.policies import get_policy_pages
from emporio_music.tools import ToolRegistry


ROOT = Path(__file__).resolve().parents[1]
TABLES = ("categories", "products", "promotions", "customers", "orders", "order_items")


def main() -> None:
    settings = Settings.from_environment(ROOT)
    source = {}
    for table in TABLES:
        candidates = [path for path in settings.raw_dir.glob("*.csv") if path.stem == table or path.stem.endswith(" - " + table)]
        assert len(candidates) == 1, f"Expected one supplied CSV for {table}."
        with candidates[0].open(encoding="utf-8-sig", newline="") as stream:
            source[table] = list(csv.DictReader(stream, strict=True))
        key = (lambda row: (row["order_id"], row["product_id"])) if table == "order_items" else (
            lambda row, column=("category_id" if table == "categories" else table[:-1] + "_id"): row[column]
        )
        assert len({key(row) for row in source[table]}) == len(source[table]), f"Duplicate key in {table}."
    for child, field, parent in (
        ("products", "category_id", "categories"), ("promotions", "product_id", "products"),
        ("orders", "customer_id", "customers"), ("order_items", "order_id", "orders"),
        ("order_items", "product_id", "products"),
    ):
        assert {row[field] for row in source[child]} <= {row[field] for row in source[parent]}, f"Broken relationship: {child}/{field}."

    with tempfile.TemporaryDirectory(prefix="emporio-source-validation-") as directory:
        database = Path(directory) / "source-check.sqlite3"
        first = import_data(settings.raw_dir, database)
        second = import_data(settings.raw_dir, database)
        counts = {table: len(rows) for table, rows in source.items()}
        assert first.counts == second.counts == counts
        with closing(sqlite3.connect(database)) as connection:
            assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
            assert {table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] for table in TABLES} == counts
            for row in source["orders"]:
                stored = connection.execute(
                    "SELECT customer_id, total_cents, tracking_code, estimated_delivery, notes "
                    "FROM orders WHERE order_id=?", (int(row["order_id"]),),
                ).fetchone()
                assert stored == (
                    int(row["customer_id"]), int(Decimal(row["total_brl"]) * 100),
                    row["tracking_code"].strip() or None,
                    row["estimated_delivery"].strip() or None,
                    row["notes"].strip() or None,
                ), "An order relationship, total, or optional field differs from its source."
            for row in source["order_items"]:
                stored = connection.execute("SELECT quantity FROM order_items WHERE order_id=? AND product_id=?", (int(row["order_id"]), int(row["product_id"]))).fetchone()[0]
                assert stored == int(row["quantity"])
            for row in source["promotions"]:
                stored = connection.execute(
                    "SELECT product_id, discount_percent, is_active FROM promotions WHERE promotion_id=?",
                    (int(row["promotion_id"]),),
                ).fetchone()
                assert stored == (
                    int(row["product_id"]), int(row["discount_percent"]), int(row["is_active"]),
                ), "A promotion relationship, percentage, or active flag differs from its source."

        available_ids = set()
        expected_guitars = []
        expected_prices = {}
        for row in source["products"]:
            identifier = int(row["product_id"])
            product = get_product(database, identifier)
            available = row["status"] == "active" and int(row["stock_quantity"]) > 0
            if available:
                available_ids.add(identifier)
            offers = [offer for offer in source["promotions"] if offer["product_id"] == row["product_id"] and offer["is_active"] == "1"]
            price = Decimal(row["price_brl"]).quantize(Decimal("0.01"))
            effective = price
            if available and len(offers) == 1:
                effective = (price * (100 - Decimal(offers[0]["discount_percent"])) / 100).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            assert product["price_brl"] == str(price)
            assert product["effective_price_brl"] == str(effective)
            assert product["stock_quantity"] == int(row["stock_quantity"])
            assert product["available"] == available
            assert product["status"] == row["status"].strip()
            assert product["category_id"] == int(row["category_id"])
            assert product["name"] == row["name"].strip()
            assert product["description"] == (row["description"].strip() or None)
            assert product["specs"] == (json.loads(row["specs"]) if row["specs"].strip() else None)
            expected_prices[identifier] = effective
            assert {offer["promotion_id"] for offer in product["active_promotions"]} == {int(offer["promotion_id"]) for offer in offers}
            if int(row["category_id"]) == 5 and available and effective <= Decimal("1000"):
                expected_guitars.append((effective, identifier))
        guitars = search_products(database, category_id=5, max_price="1000", available=True, limit=100)
        assert [row["product_id"] for row in guitars] == [identifier for _, identifier in sorted(expected_guitars)]
        assert get_product(database, 999999) is None
        assert search_products(database, "Missing-Synthetic-Instrument-999999") == []
        tools = ToolRegistry(Settings(settings.raw_dir, database, settings.policies_path))
        pix = tools.execute("quote_payment", {"product_id": 81, "payment_method": "pix"})
        expected_pix = (expected_prices[81] * Decimal("0.95")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assert pix["eligible"] and Decimal(pix["total_brl"]) == expected_pix
        promotional_pix = tools.execute("quote_payment", {"product_id": 90, "payment_method": "pix"})
        assert promotional_pix["eligible"] and Decimal(promotional_pix["total_brl"]) == expected_prices[90]
        assert promotional_pix["discounts_stacked"] is False
        credit = tools.execute("quote_payment", {"product_id": 81, "payment_method": "credit", "installments": 6})
        assert credit["eligible"] and sum(Decimal(item["amount_brl"]) * item["count"] for item in credit["installment_schedule"]) == expected_prices[81]
        assert tools.execute("quote_payment", {"product_id": 96, "payment_method": "pix"})["eligible"] is False

    reader = PdfReader(settings.policies_path)
    pages = [" ".join((page.extract_text() or "").split()) for page in reader.pages]
    retrieved = get_policy_pages(settings.policies_path, [2, 3, 4])
    assert all(page.text == pages[page.page - 1] for page in retrieved)
    assert "09:00" in pages[1] and "18:00" in pages[1] and "13:00" in pages[1]
    assert "5%" in pages[2] and "80,00" in pages[2] and "100,00" in pages[2]
    assert "7 (sete) dias" in pages[3] and "10 dias" in pages[3]
    print(json.dumps({
        "status": "PASS", "validation": "independent source comparison; no model involved",
        "counts": counts, "available_products": len(available_ids),
        "active_promotions": Counter(row["is_active"] for row in source["promotions"])["1"],
        "available_category_5_up_to_brl_1000": [row["product_id"] for row in guitars],
        "policy_pages": len(pages),
        "payment_checks": {"product_81_pix_brl": pix["total_brl"], "product_90_pix_brl": promotional_pix["total_brl"], "stacked_discounts": False, "credit_schedule_total_preserved": True},
        "checks": ["all source prices/stocks/statuses/specifications/active offers", "all promotion flags/percentages/relationships", "all quantities and stored order totals/relationships/optional fields", "foreign keys", "repeat import", "category budget filter", "missing products", "complete policy pages", "source-checked payment quotes"],
    }, indent=2))


if __name__ == "__main__":
    main()
