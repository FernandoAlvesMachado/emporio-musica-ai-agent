"""Exercise the local browser API with synthetic inputs and real HTTP requests."""

import csv
import json
import shutil
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import ProxyHandler, Request, build_opener

import pytest

from emporio_music.browser import create_server
from emporio_music.config import Settings


FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def browser(tmp_path):
    raw_dir = Path(shutil.copytree(FIXTURES / "raw", tmp_path / "data" / "raw"))
    policies_path = Path(shutil.copy(FIXTURES / "policies.pdf", raw_dir / "policies.pdf"))
    settings = Settings(raw_dir, tmp_path / "data" / "processed" / "catalog.sqlite3", policies_path)
    server = create_server(settings, port=0)
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    origin = f"http://127.0.0.1:{server.server_address[1]}"
    opener = build_opener(ProxyHandler({}))

    def request(path, method="GET", headers=None):
        operation = Request(
            origin + path, data=b"" if method == "POST" else None,
            method=method, headers=headers or {},
        )
        try:
            response = opener.open(operation, timeout=5)
        except HTTPError as error:
            response = error
        with response:
            content = response.read().decode("utf-8")
            payload = json.loads(content) if "application/json" in response.headers.get("Content-Type", "") else content
            return response.status, response.headers, payload

    try:
        yield settings, request, origin
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def load_snapshot(request):
    status, _, report = request("/api/load", "POST", {"X-Emporio-Client": "browser"})
    assert status == 200
    return report


def test_browser_loads_real_queries_and_page_referenced_policies(browser):
    _, request, _ = browser
    first = load_snapshot(request)
    assert first["counts"]["products"] == 5
    assert load_snapshot(request)["counts"] == first["counts"]
    status, _, summary = request("/api/status")
    assert status == 200
    assert summary["database_ready"] and summary["policies_ready"]
    assert summary["product_count"] == 5
    assert summary["available_count"] == 2
    assert summary["active_promotion_count"] == 1

    status, _, payload = request("/api/products?name=VIOLAO&max_price=539.91&availability=available")
    assert status == 200
    assert [product["product_id"] for product in payload["products"]] == [1]
    status, _, payload = request("/api/products/1")
    assert status == 200
    assert payload["product"]["price_brl"] == "599.90"
    assert payload["product"]["effective_price_brl"] == "539.91"
    assert payload["product"]["stock_quantity"] == 3
    status, _, payload = request("/api/policies?q=devolucao")
    assert status == 200
    assert [match["page"] for match in payload["matches"]] == [2]
    assert "Devolução" in payload["matches"][0]["text"]
    assert payload["matches"][0]["source"] == "policies.pdf"

    for route, content_type in (("/", "text/html"), ("/assets/app.css", "text/css"), ("/assets/app.js", "javascript")):
        status, headers, content = request(route)
        assert status == 200 and content
        assert content_type in headers["Content-Type"]


def test_browser_reports_missing_sources_without_creating_a_database(browser):
    settings, request, _ = browser
    status, _, summary = request("/api/status")
    assert status == 200
    assert summary["database_ready"] is False
    assert summary["product_count"] is None
    status, _, payload = request("/api/products")
    assert status == 409 and payload["code"] == "database_missing"
    assert not settings.database_path.exists()

    settings.policies_path.unlink()
    status, _, summary = request("/api/status")
    assert status == 200 and summary["policies_ready"] is False
    status, _, payload = request("/api/policies?q=devolucao")
    assert status in (400, 409) and payload["code"] == "source_error"


@pytest.mark.parametrize("query", [
    "max_price=-10", "max_price=not-money", "availability=perhaps",
    "limit=0", "limit=not-a-number",
])
def test_browser_rejects_invalid_search_filters(browser, query):
    _, request, _ = browser
    load_snapshot(request)
    status, _, payload = request("/api/products?" + query)
    assert status == 400 and payload["code"] == "invalid_request"


def test_browser_does_not_expose_private_files_or_unknown_records(browser):
    _, request, _ = browser
    load_snapshot(request)
    for path in (
        "/data/raw/customers.csv", "/data/raw/policies.pdf", "/../data/raw/customers.csv",
        "/assets/../../data/raw/customers.csv", "/assets/%2e%2e/%2e%2e/data/raw/customers.csv",
    ):
        status, _, payload = request(path)
        assert status == 404 and payload["code"] == "not_found"
    status, _, payload = request("/api/products/999")
    assert status == 404 and payload["code"] == "not_found"


def test_browser_load_rejects_cross_origin_and_form_requests(browser):
    settings, request, origin = browser
    for headers in ({}, {"X-Emporio-Client": "browser", "Origin": "https://another.example"}):
        status, _, payload = request("/api/load", "POST", headers)
        assert status in (400, 403) and "error" in payload
        assert not settings.database_path.exists()
    status, _, report = request("/api/load", "POST", {
        "X-Emporio-Client": "browser", "Origin": origin,
    })
    assert status == 200 and report["counts"]["products"] == 5


def test_browser_import_failure_preserves_the_previous_snapshot(browser):
    settings, request, _ = browser
    load_snapshot(request)
    path = settings.raw_dir / "products.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        fields, rows = reader.fieldnames, list(reader)
    rows[0]["price_brl"] = ""
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    status, _, payload = request("/api/load", "POST", {"X-Emporio-Client": "browser"})
    assert status in (400, 409) and payload["code"] == "source_error"
    status, _, payload = request("/api/products/1")
    assert status == 200 and payload["product"]["price_brl"] == "599.90"
