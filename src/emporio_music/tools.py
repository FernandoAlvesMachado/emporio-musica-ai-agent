"""Small, validated, read-only tools available to the customer-service model."""

from dataclasses import asdict

from emporio_music import catalog, policies
from emporio_music.config import Settings
from emporio_music.data import parse_money_to_cents
from emporio_music.text import normalize_text


def _definition(name: str, description: str, properties: dict, required: tuple = ()) -> dict:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "parameters": {
            "type": "object", "properties": properties, "required": list(required),
            "additionalProperties": False,
        },
    }


TOOL_DEFINITIONS = [
    _definition(
        "list_categories",
        "Read supplied category IDs and names. Use this before recommending an instrument type; "
        "product names usually contain brands/models rather than words such as acoustic guitar.",
        {},
    ),
    _definition(
        "search_products",
        "Read the actual catalog. Combine a discovered category ID, literal name fragment, "
        "inclusive effective BRL price limit and availability. Availability requires active status "
        "and positive stock; results are the supplied snapshot, not live inventory.",
        {
            "name": {"type": "string", "description": "Optional literal brand/model fragment, not a full natural-language question."},
            "category_id": {"type": "integer", "description": "Category ID obtained from list_categories."},
            "max_price": {"type": "string", "description": "Optional maximum BRL amount using a decimal point, for example 1000.00."},
            "available": {"type": "boolean", "description": "Set true when recommending products that can be sold."},
            "limit": {"type": "integer", "minimum": 1, "maximum": 20},
        },
    ),
    _definition(
        "get_product", "Read source-backed product details, stock, base price and active promotions by ID.",
        {"product_id": {"type": "integer"}}, ("product_id",),
    ),
    _definition(
        "search_policies", "Find literal words in policy excerpts with physical PDF page references. "
        "Use get_policy_pages to read complete conditions before giving rules or applying exceptions.",
        {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 5}},
        ("query",),
    ),
    _definition(
        "get_policy_pages", "Read up to three complete physical PDF pages, preserving source references. "
        "This avoids losing hours, payment tables, return conditions or exceptions to snippet truncation.",
        {"pages": {"type": "array", "items": {"type": "integer", "minimum": 1}, "minItems": 1, "maxItems": 3}},
        ("pages",),
    ),
    _definition(
        "quote_payment", "Calculate a source-checked indicative payment quote for one available product. "
        "Uses the configured manual pages 3 and 6; never combines PIX and promotions, and never executes a purchase. "
        "Ambiguous rules or offers require staff clarification instead of an invented quote.",
        {
            "product_id": {"type": "integer"},
            "payment_method": {"type": "string", "enum": ["pix", "debit", "credit", "boleto"]},
            "installments": {"type": "integer", "minimum": 1, "maximum": 12},
        },
        ("product_id", "payment_method"),
    ),
]


def _integer(value, name: str, maximum: int = 2**63 - 1) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= maximum:
        raise ValueError(f"{name} must be an integer between 1 and {maximum}.")
    return value


def _money(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d}"


def _error(code: str, message: str) -> dict:
    return {"error": code, "message": message}


class ToolRegistry:
    """Dispatch only allowlisted queries; model arguments never select files or SQL."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def execute(self, name: str, arguments: dict) -> dict:
        definition = next((item for item in TOOL_DEFINITIONS if item["name"] == name), None)
        if definition is None:
            return _error("unknown_tool", "This operation is not available; no action was executed.")
        if not isinstance(arguments, dict):
            return _error("invalid_arguments", "Tool arguments must be an object.")
        schema = definition["parameters"]
        if set(arguments) - schema["properties"].keys():
            return _error("invalid_arguments", "The request contains unsupported fields.")
        if set(schema["required"]) - arguments.keys():
            return _error("invalid_arguments", "A required tool argument is missing.")
        try:
            if name == "list_categories":
                return {"categories": catalog.list_categories(self.settings.database_path), "source_kind": "catalog_snapshot"}
            if name == "search_products":
                query = arguments.get("name", "")
                if not isinstance(query, str) or len(query) > 200:
                    raise ValueError("Name must be a string of at most 200 characters.")
                maximum = arguments.get("max_price")
                if maximum is not None and not isinstance(maximum, str):
                    raise ValueError("Maximum price must be an exact decimal string.")
                limit = _integer(arguments.get("limit", 10), "Limit", 20)
                products = catalog.search_products(
                    self.settings.database_path, name=query, max_price=maximum,
                    available=arguments.get("available"), limit=limit,
                    category_id=arguments.get("category_id"),
                )
                return {"products": products, "source_kind": "catalog_snapshot", "result_limit": limit}
            if name == "get_product":
                identifier = _integer(arguments["product_id"], "Product ID")
                product = catalog.get_product(self.settings.database_path, identifier)
                if product is None:
                    return _error("not_found", "No supplied product matches this identifier.")
                return {"product": product, "source_kind": "catalog_snapshot"}
            if name == "search_policies":
                query = arguments["query"]
                if not isinstance(query, str):
                    raise ValueError("Policy query must be a string.")
                matches = policies.search_policies(
                    self.settings.policies_path, query, _integer(arguments.get("limit", 5), "Limit", 5)
                )
                return {"matches": [asdict(match) for match in matches], "source_kind": "policy_pdf"}
            if name == "get_policy_pages":
                pages = policies.get_policy_pages(self.settings.policies_path, arguments["pages"])
                return {"pages": [asdict(page) for page in pages], "source_kind": "policy_pdf"}
            return self._quote_payment(arguments)
        except catalog.CatalogError:
            return _error("catalog_unavailable", "The catalog snapshot is missing or unreadable. Ask staff to load the source data.")
        except policies.PolicyError:
            return _error("policies_unavailable", "The configured policy PDF is missing or unreadable. Ask staff to verify the source.")
        except (ValueError, TypeError, OverflowError):
            return _error("invalid_arguments", "Arguments are invalid for this tool. Check its declared types and limits.")
        except OSError:
            return _error("source_unavailable", "The configured source could not be read. No unsupported information was inferred.")

    def _quote_payment(self, arguments: dict) -> dict:
        identifier = _integer(arguments["product_id"], "Product ID")
        method = arguments["payment_method"]
        if not isinstance(method, str) or method not in {"pix", "debit", "credit", "boleto"}:
            raise ValueError("Unsupported payment method.")
        installments = _integer(arguments.get("installments", 1), "Installments", 12)
        if method != "credit" and installments != 1:
            raise ValueError("Installments apply only to credit-card payments.")
        product = catalog.get_product(self.settings.database_path, identifier)
        if product is None:
            return _error("not_found", "No supplied product matches this identifier.")
        if not product["available"]:
            return {"eligible": False, "product_id": identifier, "reason": "Product unavailable; no purchase price is offered."}
        if product["promotion_note"]:
            return {"eligible": None, "needs_staff_confirmation": True, "reason": product["promotion_note"], "product_id": identifier}
        try:
            source_pages = policies.get_policy_pages(self.settings.policies_path, [3, 6])
        except ValueError:
            return _error("policy_rules_unverified", "The configured manual does not provide the required payment and promotion pages; ask staff to confirm conditions.")
        payment_text = normalize_text(source_pages[0].text)
        promotion_text = normalize_text(source_pages[1].text)
        payment_clauses = (
            "pix pagamento a vista 5% de desconto sobre o preco de tabela",
            "cartao de debito", "boleto bancario", "3.1 regras de parcelamento",
            "parcelamento em ate 3x: sem juros, sem valor minimo de parcela (exceto abaixo de r$ 50,00)",
            "parcelamento de 4x a 6x: sem juros, parcela minima de r$ 80,00",
            "parcelamento de 7x a 12x: sem juros, parcela minima de r$ 100,00",
        )
        promotion_clauses = (
            "promocoes nao sao cumulativas",
            "o desconto de pix (5%) nao se aplica sobre precos ja promocionais",
        )
        if not all(clause in payment_text for clause in payment_clauses) or not all(clause in promotion_text for clause in promotion_clauses):
            return _error("policy_rules_unverified", "The configured manual's rules differ from the implemented payment calculation; ask staff to confirm conditions.")
        source = [{"source": page.source, "page": page.page} for page in source_pages]
        base = parse_money_to_cents(product["price_brl"])
        effective = parse_money_to_cents(product["effective_price_brl"])
        promotional = bool(product["active_promotions"])
        total = (base * 95 + 50) // 100 if method == "pix" and not promotional else effective
        result = {
            "product_id": identifier, "product_name": product["name"], "payment_method": method,
            "installments": installments, "base_price_brl": product["price_brl"],
            "catalog_price_brl": product["effective_price_brl"], "total_brl": _money(total),
            "discount_percent": product["active_promotions"][0]["discount_percent"] if promotional else (5 if method == "pix" else 0),
            "discounts_stacked": False, "eligible": True, "policy_references": source,
            "source_kind": "catalog_and_policy_calculation",
            "note": "Indicative quote from the supplied snapshot; no purchase, reservation or payment was executed.",
        }
        if method == "credit":
            if installments <= 3 and total < installments * 10000:
                result.update(
                    eligible=None, needs_staff_confirmation=True,
                    reason="The general minimum and the detailed up-to-three-installment exception are ambiguous for this amount; staff must confirm before offering installments.",
                )
            elif installments >= 4:
                minimum = 8000 if installments <= 6 else 10000
                result["minimum_installment_brl"] = _money(minimum)
                result["eligible"] = total >= installments * minimum
                if not result["eligible"]:
                    result["reason"] = "The requested installments fall below the detailed policy's minimum."
                result["interpretation"] = "The explicit installment tiers in section 3.1 take precedence over the general payment-table summary."
            # Preserve the total exactly when cents cannot be split equally.
            if result["eligible"] is True:
                quotient, remainder = divmod(total, installments)
                result["installment_schedule"] = [
                    {"count": remainder, "amount_brl": _money(quotient + 1)},
                    {"count": installments - remainder, "amount_brl": _money(quotient)},
                ] if remainder else [{"count": installments, "amount_brl": _money(quotient)}]
        if method == "boleto":
            result["settlement_note"] = "The manual states settlement in up to three business days (page 3); no payment was issued."
        return result
