"""Loopback-only development web interface using the existing data tools."""

from __future__ import annotations

import json
import webbrowser
from dataclasses import asdict
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from urllib.parse import parse_qs, urlsplit

from emporio_music.catalog import (
    CatalogError,
    get_catalog_summary,
    get_product,
    search_products,
)
from emporio_music.config import Settings
from emporio_music.data import DataValidationError, import_data
from emporio_music.policies import PolicyError, search_policies


_ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/assets/app.css": ("app.css", "text/css; charset=utf-8"),
    "/assets/app.js": ("app.js", "text/javascript; charset=utf-8"),
}


class BrowserServer(ThreadingHTTPServer):
    """Local development server; raw source files are never served."""

    daemon_threads = True

    def __init__(self, settings: Settings, port: int):
        if not isinstance(port, int) or isinstance(port, bool) or not 0 <= port <= 65535:
            raise ValueError("Port must be an integer between 0 and 65535.")
        self.settings = settings
        super().__init__(("127.0.0.1", port), BrowserHandler)
        actual_port = self.server_address[1]
        self.allowed_hosts = {f"127.0.0.1:{actual_port}", f"localhost:{actual_port}"}
        self.allowed_origins = {f"http://{host}" for host in self.allowed_hosts}
        self.url = f"http://127.0.0.1:{actual_port}"


class BrowserHandler(BaseHTTPRequestHandler):
    server: BrowserServer
    server_version = "EmporioDevelopment"

    def log_message(self, format: str, *args) -> None:
        # Do not persist request text or accidental personal data in query strings.
        pass

    def _send(self, status: int, content: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'",
        )
        self.end_headers()
        self.wfile.write(content)

    def _json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def _error(self, status: int, code: str, message: str) -> None:
        self._json({"error": message, "code": code}, status)

    def _trusted_request(self) -> bool:
        if self.headers.get("Host") not in self.server.allowed_hosts:
            self._error(HTTPStatus.FORBIDDEN, "invalid_request", "Only local browser requests are supported.")
            return False
        if len(self.path) > 4096:
            self._error(HTTPStatus.REQUEST_URI_TOO_LONG, "invalid_request", "Request URL is too long.")
            return False
        return True

    def _status(self) -> dict:
        summary = {"product_count": None, "available_count": None, "active_promotion_count": None}
        ready = False
        try:
            summary = get_catalog_summary(self.server.settings.database_path)
            ready = True
        except CatalogError:
            pass
        return {
            "database_ready": ready,
            "policies_ready": self.server.settings.policies_path.is_file(),
            **summary,
        }

    def _query(self) -> tuple[str, dict[str, str]]:
        target = urlsplit(self.path)
        values = parse_qs(target.query, keep_blank_values=True, max_num_fields=12)
        if any(len(items) != 1 for items in values.values()):
            raise ValueError("Each query parameter must appear only once.")
        return target.path, {key: items[0] for key, items in values.items()}

    @staticmethod
    def _limit(query: dict[str, str], default: int, maximum: int) -> int:
        limit = int(query.get("limit", str(default)))
        if not 1 <= limit <= maximum:
            raise ValueError(f"Result limit must be between 1 and {maximum}.")
        return limit

    def do_GET(self) -> None:
        if not self._trusted_request():
            return
        try:
            path, query = self._query()
            if path in _ASSETS:
                filename, content_type = _ASSETS[path]
                content = files("emporio_music").joinpath("web", filename).read_bytes()
                self._send(HTTPStatus.OK, content, content_type)
            elif path == "/api/status":
                self._json(self._status())
            elif path == "/api/products":
                availability = query.get("availability", "all")
                if availability not in {"all", "available", "unavailable"}:
                    raise ValueError("Availability must be all, available, or unavailable.")
                name = query.get("name", "")
                if len(name) > 200:
                    raise ValueError("Product name queries must contain at most 200 characters.")
                products = search_products(
                    self.server.settings.database_path,
                    name=name,
                    max_price=query.get("max_price") or None,
                    available={"all": None, "available": True, "unavailable": False}[availability],
                    limit=self._limit(query, 100, 100),
                )
                self._json({"products": products})
            elif path.startswith("/api/products/"):
                product_id = int(path.removeprefix("/api/products/"))
                product = get_product(self.server.settings.database_path, product_id)
                if product is None:
                    self._error(HTTPStatus.NOT_FOUND, "not_found", "Product not found.")
                else:
                    self._json({"product": product})
            elif path == "/api/policies":
                matches = search_policies(
                    self.server.settings.policies_path,
                    query.get("q", ""),
                    self._limit(query, 5, 20),
                )
                self._json({"matches": [asdict(match) for match in matches]})
            else:
                self._error(HTTPStatus.NOT_FOUND, "not_found", "Resource not found.")
        except CatalogError:
            self._error(HTTPStatus.CONFLICT, "database_missing", "Load the source data to create a valid catalog snapshot.")
        except PolicyError:
            self._error(HTTPStatus.BAD_REQUEST, "source_error", "The policy PDF is missing or cannot be read. Check the configured source file.")
        except (ValueError, OverflowError) as error:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_request", str(error))
        except OSError:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "Local files could not be read.")

    def do_POST(self) -> None:
        if not self._trusted_request():
            return
        if self.headers.get("X-Emporio-Client") != "browser" or (
            self.headers.get("Origin") is not None
            and self.headers.get("Origin") not in self.server.allowed_origins
        ):
            self._error(HTTPStatus.FORBIDDEN, "invalid_request", "Import requests must come from the local application.")
            return
        if self.path != "/api/load":
            self._error(HTTPStatus.NOT_FOUND, "not_found", "Resource not found.")
            return
        try:
            report = import_data(self.server.settings.raw_dir, self.server.settings.database_path)
            self._json(asdict(report))
        except DataValidationError as error:
            self._error(HTTPStatus.BAD_REQUEST, "source_error", str(error))
        except OSError:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "internal_error", "The catalog snapshot could not be written.")


def create_server(settings: Settings, port: int = 8000) -> BrowserServer:
    """Create a server without starting a thread, allowing deterministic tests."""
    return BrowserServer(settings, port)


def serve(settings: Settings, port: int = 8000, open_browser: bool = False) -> None:
    """Serve the local interface until Ctrl+C, without changing source data."""
    with create_server(settings, port) as server:
        print(f"Local browser interface: {server.url}", flush=True)
        print("Press Ctrl+C to stop. LLM integration is pending.", flush=True)
        if open_browser:
            try:
                if not webbrowser.open(server.url):
                    print("Open the local URL above in your browser.", flush=True)
            except webbrowser.Error:
                print("Open the local URL above in your browser.", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nLocal browser interface stopped.", flush=True)
