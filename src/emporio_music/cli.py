"""Development CLI: real data queries, with no language-model integration."""

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

from emporio_music.catalog import get_product, search_products
from emporio_music.config import Settings
from emporio_music.data import import_data
from emporio_music.policies import export_policy_pages, search_policies


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Emporio da Musica development CLI. LLM integration is pending."
    )
    parser.add_argument("--root", type=Path, help="Project root for relative data paths (default: working directory).")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("load", help="Validate and atomically import all six CSV files into SQLite.")
    search = commands.add_parser("search", help="Search product names and filter actual catalog data.")
    search.add_argument("name", nargs="?", default="", help="Literal name fragment, ignoring case and accents.")
    search.add_argument("--max-price", help="Inclusive effective BRL price, decimal point, e.g. 1000.00.")
    availability = search.add_mutually_exclusive_group()
    availability.add_argument("--available", dest="available", action="store_const", const=True)
    availability.add_argument("--unavailable", dest="available", action="store_const", const=False)
    search.add_argument("--limit", type=int, default=20)
    product = commands.add_parser("product", help="Show product details by ID.")
    product.add_argument("product_id", type=int)
    policies = commands.add_parser("policies", help="Find source policy excerpts with PDF page references.")
    policies.add_argument("query")
    policies.add_argument("--limit", type=int, default=5)
    extract = commands.add_parser("extract-policies", help="Export PDF text to page-referenced JSON.")
    extract.add_argument("--output", type=Path, default=Path("data/processed/policies.json"))
    browser = commands.add_parser("serve", help="Start the local browser interface for catalog and policies.")
    browser.add_argument("--port", type=int, default=8000)
    browser.add_argument("--open-browser", action="store_true", help="Open the local interface in the default browser.")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows redirected streams may default to a legacy encoding. Preserve accents.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    print("Development CLI: LLM integration is pending.", file=sys.stderr)
    try:
        settings = Settings.from_environment(args.root)
        if args.command == "serve":
            from emporio_music.browser import serve

            serve(settings, port=args.port, open_browser=args.open_browser)
            return 0
        if args.command == "load":
            payload = asdict(import_data(settings.raw_dir, settings.database_path))
        elif args.command == "search":
            payload = search_products(
                settings.database_path, args.name, args.max_price, args.available, args.limit
            )
        elif args.command == "product":
            payload = get_product(settings.database_path, args.product_id)
            if payload is None:
                print(f"Product {args.product_id} was not found.", file=sys.stderr)
                return 1
        elif args.command == "policies":
            payload = [asdict(match) for match in search_policies(
                settings.policies_path, args.query, args.limit
            )]
        else:
            output = args.output.expanduser().resolve()
            pages = export_policy_pages(settings.policies_path, output)
            payload = {"pages": pages, "output": str(output)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
