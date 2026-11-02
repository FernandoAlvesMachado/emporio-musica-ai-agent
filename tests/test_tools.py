"""Isolated source-tool tests; these do not exercise an external language model."""

from pathlib import Path

import pytest

from emporio_music import policies
from emporio_music.config import Settings
from emporio_music.data import import_data, parse_money_to_cents
from emporio_music.tools import ToolRegistry


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def registry(tmp_path):
    settings = Settings(FIXTURES / "raw", tmp_path / "catalog.sqlite3", FIXTURES / "policies.pdf")
    import_data(settings.raw_dir, settings.database_path)
    return ToolRegistry(settings)


@pytest.fixture
def recognized_payment_rules(monkeypatch):
    """Stub recognized clauses to isolate arithmetic, not prove original-PDF behavior."""
    payment = (
        "Synthetic payment reference. PIX Pagamento à vista 5% de desconto sobre o preço de tabela. "
        "Cartão de Débito. Boleto Bancário. 3.1 Regras de Parcelamento. "
        "Parcelamento em até 3x: sem juros, sem valor mínimo de parcela (exceto abaixo de R$ 50,00). "
        "Parcelamento de 4x a 6x: sem juros, parcela mínima de R$ 80,00. "
        "Parcelamento de 7x a 12x: sem juros, parcela mínima de R$ 100,00."
    )
    promotions = (
        "Synthetic promotion reference. Promoções não são cumulativas. "
        "O desconto de PIX (5%) não se aplica sobre preços já promocionais."
    )

    def pages(_path, _numbers):
        return [
            policies.PolicyMatch(3, payment, "synthetic-payment-reference.pdf"),
            policies.PolicyMatch(6, promotions, "synthetic-payment-reference.pdf"),
        ]

    monkeypatch.setattr(policies, "get_policy_pages", pages)


def test_category_discovery_and_category_budget_filters(registry):
    categories = registry.execute("list_categories", {})["categories"]
    assert [category["category_id"] for category in categories] == [1, 2]
    result = registry.execute("search_products", {
        "category_id": 1, "available": True, "max_price": "539.91",
    })
    assert [product["product_id"] for product in result["products"]] == [1]
    assert result["products"][0]["effective_price_brl"] == "539.91"
    assert registry.execute("search_products", {"category_id": 2, "available": True})["products"] == []
    assert registry.execute("get_product", {"product_id": 999})["error"] == "not_found"
    assert registry.execute("get_product", {"product_id": 2})["product"]["available"] is False


def test_dispatch_does_not_expose_arbitrary_operations_or_sources(registry):
    assert registry.execute("get_orders", {"customer_id": 1})["error"] == "unknown_tool"
    assert registry.execute("get_product", {"product_id": 1, "sql": "SELECT * FROM customers"})["error"] == "invalid_arguments"
    for arguments in ({"limit": 21}, {"available": "yes"}, {"category_id": True}, {"max_price": 12.34}):
        assert registry.execute("search_products", arguments)["error"] == "invalid_arguments"
    assert registry.execute("get_policy_pages", {"pages": [1], "path": "secret.pdf"})["error"] == "invalid_arguments"


def test_full_policy_pages_preserve_conditions_and_references(registry):
    result = registry.execute("get_policy_pages", {"pages": [1, 2]})
    assert [page["page"] for page in result["pages"]] == [1, 2]
    assert "10h às 17h" in result["pages"][0]["text"]
    assert all(page["source"] == "policies.pdf" for page in result["pages"])
    for pages in ([], [0], [3], [1, 1], [1, 2, 3, 4], [True]):
        assert registry.execute("get_policy_pages", {"pages": pages})["error"] == "invalid_arguments"


def test_payment_quote_refuses_rules_not_present_in_configured_manual(registry):
    result = registry.execute("quote_payment", {"product_id": 1, "payment_method": "pix"})
    assert result["error"] == "policy_rules_unverified"
    assert "total_brl" not in result


def test_pix_uses_exact_money_without_stacking_promotions(registry, recognized_payment_rules):
    promotional = registry.execute("quote_payment", {"product_id": 1, "payment_method": "pix"})
    assert promotional["total_brl"] == "539.91"
    assert promotional["discount_percent"] == 10
    assert promotional["discounts_stacked"] is False
    ordinary = registry.execute("quote_payment", {"product_id": 5, "payment_method": "pix"})
    assert ordinary["total_brl"] == "1140.00"
    assert ordinary["discount_percent"] == 5
    assert ordinary["eligible"] is True
    assert [reference["page"] for reference in ordinary["policy_references"]] == [3, 6]
    unavailable = registry.execute("quote_payment", {"product_id": 2, "payment_method": "pix"})
    assert unavailable["eligible"] is False and "total_brl" not in unavailable


def test_credit_tiers_and_cent_splits_do_not_offer_invalid_installments(registry, recognized_payment_rules):
    six = registry.execute("quote_payment", {"product_id": 1, "payment_method": "credit", "installments": 6})
    assert six["eligible"] is True
    assert six["minimum_installment_brl"] == "80.00"
    assert sum(item["count"] * parse_money_to_cents(item["amount_brl"]) for item in six["installment_schedule"]) == 53991
    twelve = registry.execute("quote_payment", {"product_id": 1, "payment_method": "credit", "installments": 12})
    assert twelve["eligible"] is False
    assert "installment_schedule" not in twelve
    assert registry.execute("quote_payment", {"product_id": 1, "payment_method": "pix", "installments": 2})["error"] == "invalid_arguments"
