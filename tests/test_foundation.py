"""Exercise the foundation against small, exclusively synthetic source files."""

import csv
import json
import shutil
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from pypdf import PdfWriter

from emporio_music.catalog import CatalogError, get_product, search_products
from emporio_music.cli import main
from emporio_music.data import HEADERS, DataValidationError, import_data, parse_money_to_cents
from emporio_music.policies import (
    PolicyError,
    export_policy_pages,
    extract_policy_pages,
    search_policies,
)


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def raw_dir(tmp_path):
    return Path(shutil.copytree(FIXTURES / "raw", tmp_path / "data" / "raw"))


@pytest.fixture
def database(raw_dir, tmp_path):
    path = tmp_path / "data" / "processed" / "emporio.sqlite3"
    import_data(raw_dir, path)
    return path


def rewrite_csv(path, change):
    """Apply a test-only mutation while retaining proper CSV quoting."""
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    change(rows)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def snapshot(database):
    with closing(sqlite3.connect(database)) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in HEADERS
        }


def test_repeated_import_is_idempotent_and_removes_obsolete_rows(raw_dir, database):
    before = snapshot(database)
    report = import_data(raw_dir, database)
    assert report.counts == {
        "categories": 2, "products": 5, "promotions": 2,
        "customers": 1, "orders": 1, "order_items": 1,
    }
    assert snapshot(database) == before

    rewrite_csv(raw_dir / "products.csv", lambda rows: rows.pop())
    assert import_data(raw_dir, database).counts["products"] == 4
    assert get_product(database, 5) is None


def test_product_details_preserve_exact_money_stock_and_specs(database):
    product = get_product(database, 1)
    assert product["price_brl"] == "599.90"
    assert product["stock_quantity"] == 3
    assert product["effective_price_brl"] == "539.91"
    assert product["specs"] == {"strings": 6}
    assert product["available"] is True
    assert [offer["discount_percent"] for offer in product["active_promotions"]] == [10]
    assert get_product(database, 999) is None


def test_search_combines_accent_case_price_and_availability_filters(database):
    matches = search_products(database, "VIOLAO", max_price="539.91", available=True)
    assert [product["product_id"] for product in matches] == [1]
    assert search_products(database, "violão", max_price="539.90", available=True) == []
    assert {product["product_id"] for product in search_products(database, available=True)} == {1, 5}
    assert {product["product_id"] for product in search_products(database, available=False)} == {2, 3, 4}


def test_search_treats_sql_and_wildcards_as_literal_name_text(database):
    for name in ("%", "_", "' OR 1=1 --"):
        assert search_products(database, name) == []
    assert get_product(database, 1)["price_brl"] == "599.90"


@pytest.mark.parametrize(
    ("table", "field", "value"),
    [
        ("products", "price_brl", "12,34"),
        ("products", "price_brl", ""),
        ("products", "stock_quantity", "-1"),
        ("promotions", "is_active", "true"),
        ("products", "category_id", "999"),
        ("products", "created_at", "2025-02-30"),
        ("products", "specs", "{invalid"),
        ("customers", "customer_id", ""),
    ],
)
def test_invalid_required_data_rejects_import_and_preserves_snapshot(
    raw_dir, database, table, field, value,
):
    before = snapshot(database)
    rewrite_csv(raw_dir / f"{table}.csv", lambda rows: rows[0].__setitem__(field, value))
    with pytest.raises(DataValidationError, match=field):
        import_data(raw_dir, database)
    assert snapshot(database) == before


def test_missing_source_file_preserves_previous_snapshot(raw_dir, database):
    before = snapshot(database)
    (raw_dir / "categories.csv").unlink()
    with pytest.raises(DataValidationError, match="categories.*found 0"):
        import_data(raw_dir, database)
    assert snapshot(database) == before


def test_optional_missing_values_remain_null_without_fabricated_details(database):
    assert get_product(database, 5)["description"] is None
    assert get_product(database, 5)["specs"] is None
    with closing(sqlite3.connect(database)) as connection:
        assert connection.execute("SELECT phone FROM customers").fetchone() == (None,)
        assert connection.execute(
            "SELECT tracking_code, estimated_delivery, notes FROM orders"
        ).fetchone() == (None, None, None)


def test_multiple_active_promotions_require_clarification(raw_dir, database):
    rewrite_csv(raw_dir / "promotions.csv", lambda rows: rows.append({
        "promotion_id": "3", "product_id": "1", "discount_percent": "20",
        "description": "Synthetic conflicting offer", "is_active": "1",
    }))
    report = import_data(raw_dir, database)
    product = get_product(database, 1)
    assert product["effective_price_brl"] == "599.90"
    assert len(product["active_promotions"]) == 2
    assert "confirm" in product["promotion_note"]
    assert any("multiple active promotions" in warning for warning in report.warnings)


def test_large_prices_keep_integer_precision_and_query_bounds(raw_dir, database):
    maximum = "92233720368547758.07"
    rewrite_csv(raw_dir / "products.csv", lambda rows: rows[0].__setitem__("price_brl", maximum))
    import_data(raw_dir, database)
    product = get_product(database, 1)
    assert product["price_brl"] == maximum
    assert product["effective_price_brl"] == "83010348331692982.26"
    with pytest.raises(ValueError, match="capacity"):
        parse_money_to_cents("92233720368547758.08")
    with pytest.raises(ValueError, match="SQLite integer"):
        get_product(database, 2**63)
    with pytest.raises(ValueError, match="SQLite integer"):
        search_products(database, limit=2**63)


def test_policy_search_preserves_original_accents_and_physical_pages(tmp_path):
    source = FIXTURES / "policies.pdf"
    assert [page.page for page in extract_policy_pages(source)] == [1, 2]
    returns = search_policies(source, "DEVOLUCAO")
    assert len(returns) == 1
    assert returns[0].page == 2
    assert "Devolução" in returns[0].text
    assert returns[0].source == "policies.pdf"
    hours = search_policies(source, "horario")
    assert len(hours) == 1 and hours[0].page == 1
    assert "Horário" in hours[0].text
    assert search_policies(source, "unrelatedword") == []

    output = tmp_path / "export" / "policies.json"
    assert export_policy_pages(source, output) == 2
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == "policies.pdf"
    assert [page["page"] for page in payload["pages"]] == [1, 2]
    assert "Devolução" in payload["pages"][1]["text"]

    protected_csv = tmp_path / "products.csv"
    protected_csv.write_text("original source\n", encoding="utf-8")
    with pytest.raises(PolicyError, match=".json extension"):
        export_policy_pages(source, protected_csv)
    assert protected_csv.read_text(encoding="utf-8") == "original source\n"


def test_policy_extraction_rejects_missing_and_image_only_sources(tmp_path):
    with pytest.raises(PolicyError, match="not found"):
        extract_policy_pages(tmp_path / "missing.pdf")
    blank_pdf = tmp_path / "blank.pdf"
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.write(blank_pdf)
    with pytest.raises(PolicyError, match="page 1.*OCR"):
        extract_policy_pages(blank_pdf)


def test_cli_load_search_and_policy_commands_use_actual_synthetic_sources(
    raw_dir, tmp_path, monkeypatch, capsys,
):
    for variable in (
        "EMPORIO_PROJECT_ROOT", "EMPORIO_RAW_DIR", "EMPORIO_DATABASE_PATH",
        "EMPORIO_POLICIES_PATH",
    ):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv("EMPORIO_POLICIES_PATH", str(FIXTURES / "policies.pdf"))
    arguments = ["--root", str(tmp_path)]
    assert main([*arguments, "load"]) == 0
    output = capsys.readouterr()
    assert "LLM integration is pending" in output.err
    assert json.loads(output.out)["counts"]["products"] == 5
    assert main([*arguments, "search", "violao", "--max-price", "539.91", "--available"]) == 0
    assert [row["product_id"] for row in json.loads(capsys.readouterr().out)] == [1]
    assert main([*arguments, "policies", "devolucao"]) == 0
    assert [row["page"] for row in json.loads(capsys.readouterr().out)] == [2]


def test_cli_reports_missing_product_and_database(database, tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("EMPORIO_DATABASE_PATH", str(database))
    assert main(["product", "999"]) == 1
    assert "not found" in capsys.readouterr().err
    missing = tmp_path / "missing.sqlite3"
    monkeypatch.setenv("EMPORIO_DATABASE_PATH", str(missing))
    assert main(["product", "1"]) == 2
    assert "Run 'emporio load' first" in capsys.readouterr().err
    with pytest.raises(CatalogError, match="missing"):
        search_products(missing)
    assert not missing.exists()
