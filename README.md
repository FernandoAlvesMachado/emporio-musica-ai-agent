# Emporio da Musica AI Agent

Python foundation for the Artefact AI Engineer challenge: a customer-service
assistant for a fictional musical-instrument store in Campo Grande, Brazil.

**Stage 1 is implemented: validated SQLite imports, real catalog queries, PDF policy
extraction, lexical policy search, and a development terminal CLI. LLM integration
is pending.** This CLI does not accept conversational requests, simulate an agent,
or implement a customer-facing persona or out-of-scope routing yet.

## Installation

Requires Python 3.11+ and Git. Run from the repository root.

```sh
python -m venv .venv
```

Activate on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Activate on Linux/macOS:

```sh
source .venv/bin/activate
```

Install runtime and test dependencies:

```sh
python -m pip install -e ".[dev]"
```

Activation is optional: use `.venv\Scripts\python.exe` on Windows or
`.venv/bin/python` on Linux in place of `python`. No API key or provider account is
needed. `pypdf` is the only runtime dependency; CSV, SQLite, configuration, and CLI
use the standard library. Tests use `pytest`.

## Supplied materials

Keep originals unchanged and place them locally as follows:

```text
docs/reference/desafio_tecnico_ai_eng_artefact.pdf
data/raw/desafio_tecnico_ai_eng - categories.csv
data/raw/desafio_tecnico_ai_eng - products.csv
data/raw/desafio_tecnico_ai_eng - promotions.csv
data/raw/desafio_tecnico_ai_eng - customers.csv
data/raw/desafio_tecnico_ai_eng - orders.csv
data/raw/desafio_tecnico_ai_eng - order_items.csv
data/raw/políticas_da_loja.pdf
```

CSV names may also be `categories.csv`, `products.csv`, `promotions.csv`,
`customers.csv`, `orders.csv`, and `order_items.csv`. Exactly one file per table is
required; ambiguous matches fail. Files use comma-separated UTF-8, optionally with
a BOM. Column order is flexible; missing, duplicate, or unexpected columns fail.

The source files, including the internal PDF and challenge brief, are excluded from
Git. The repository contains synthetic fixtures so tests work without the originals.
All six CSVs are imported locally, including customers and orders; the development
CLI exposes only catalog and policy queries. The SQLite database contains personal
customer data and must remain local. Do not commit it or publish raw inputs.

## Configuration

Defaults are relative to the working directory. Use `pathlib` paths on either
Windows or Linux. `.env.example` documents these optional environment variables:

| Variable | Default |
| --- | --- |
| `EMPORIO_PROJECT_ROOT` | `.` |
| `EMPORIO_RAW_DIR` | `data/raw` |
| `EMPORIO_DATABASE_PATH` | `data/processed/emporio.sqlite3` |
| `EMPORIO_POLICIES_PATH` | `data/raw/políticas_da_loja.pdf` |

Absolute paths are accepted. Relative data paths resolve against the project root.
`--root PATH` overrides `EMPORIO_PROJECT_ROOT` and must precede the subcommand.
Environment variables must be set in the shell; copying `.env.example` to `.env`
does not load it automatically. No credentials are configured in this stage.

## Development commands

```sh
python -m emporio_music --help
python -m emporio_music load
python -m emporio_music search Yamaha --max-price 1000 --available
python -m emporio_music search --unavailable
python -m emporio_music product 81
python -m emporio_music product 90
python -m emporio_music policies devolucao
python -m emporio_music policies "promocoes cumulativas"
python -m emporio_music extract-policies
```

The installed `emporio` command provides the same interface. Each executed
subcommand identifies the pending LLM integration on stderr; results are JSON on
stdout. Catalog queries read SQLite rather than hardcoded responses. Re-run `load`
after updating inputs. Policy search reads the configured PDF directly.

`search` matches a literal name fragment, ignoring case and accents. `%` and `_`
are literal characters, not SQL wildcards. `--max-price` uses a decimal point and
filters the **effective price**, inclusively. Results sort by effective price and
product ID; default limit is 20 (`--limit N`). Omitting the availability flag shows
all statuses. `--available` and `--unavailable` are mutually exclusive.
Name matching has no category inference or stemming. For example, the original
guitar names contain brands/models rather than the word `violao`, so use `Yamaha`
for the source-data demonstration; `violao` matches the synthetic fixture names.

Details include source stock/status/specifications, base price, effective price,
and active promotion records. BRL amounts are exact two-decimal strings. A missing
product exits with status 1; invalid data/configuration exits with status 2.
Empty search results are `[]`, never invented alternatives.

`policies` requires every query word on the same page, ignores case/accents, and
returns bounded original-text excerpts, source filename, and physical page number
(starting at 1, including the cover). It ranks matching pages by query-word count,
then page number. It does not expand synonyms or resolve conflicting rules.
`extract-policies` writes page-referenced UTF-8 JSON to
`data/processed/policies.json`; `--output PATH` changes the destination, resolving
relative output paths from the working directory.
Only `.json` export destinations are accepted, protecting original CSV/PDF files
from accidental overwrite. Git treats the synthetic PDF fixture as binary so
Windows/Linux line-ending conversion cannot corrupt it.

For a demonstration without original materials, set `EMPORIO_RAW_DIR` to
`tests/fixtures/raw` and `EMPORIO_POLICIES_PATH` to `tests/fixtures/policies.pdf`,
then run `load`, `search violao --available`, `product 1`, and `policies devolucao`.
Use a different `EMPORIO_DATABASE_PATH` to keep this synthetic snapshot separate.

## Structure

```text
src/emporio_music/
  config.py       # Environment and portable path configuration
  data.py         # CSV validation, schema, atomic snapshot import
  catalog.py      # Parameterized SQLite searches and product details
  policies.py     # PDF extraction, page references, lexical retrieval
  text.py         # Shared accent/case normalization
  cli.py          # Deterministic development commands
data/raw/         # Local unchanged source files (ignored)
data/processed/   # Generated SQLite and extracted JSON (ignored)
docs/reference/   # Local challenge brief (ignored)
examples/conversations/  # Reserved for future verified conversations
tests/fixtures/   # Small synthetic CSVs and two-page PDF
```

## Source audit

The three-page challenge brief, all six CSVs, and the eight-page store policy PDF
were read before implementation. The source CSVs have these fields and row counts:

| Table | Rows | Source columns |
| --- | ---: | --- |
| categories | 9 | `category_id`, `name`, `description` |
| products | 65 | `product_id`, `price_brl`, `name`, `category_id`, `description`, `stock_quantity`, `status`, `specs`, `created_at` |
| promotions | 25 | `promotion_id`, `product_id`, `discount_percent`, `description`, `is_active` |
| customers | 50 | `customer_id`, `name`, `phone`, `email`, `city` |
| orders | 20 | `order_id`, `customer_id`, `order_date`, `status`, `total_brl`, `payment_method`, `tracking_code`, `estimated_delivery`, `notes` |
| order_items | 22 | `order_id`, `quantity`, `product_id` |

Products reference categories; promotions reference products; orders reference
customers; order items reference orders and products. `(order_id, product_id)` is
the order-item key because no separate item identifier is provided. The originals
have no duplicate primary keys, malformed row widths, or broken foreign keys.

IDs are positive integers, dates are ISO `YYYY-MM-DD`, and `specs` contains quoted
JSON objects. Money uses a decimal point with variable precision (`599.9`, `849`);
promotion flags are `0`/`1`, and discounts are integer percentages. Product IDs
81–145 are not sorted in the source. Categories 6, 7, and 8 have no supplied products.
The manual describes over 300 instruments, while the CSV snapshot contains 65;
catalog answers use only the supplied rows.

## Decisions and data limitations

- **Small architecture:** SQLite handles relationships and filters; standard-library
  modules handle orchestration. No agent framework, API server, vector database,
  infrastructure service, or generic repository abstraction is needed for this stage.
- **Reproducible snapshots:** all six files are validated before any write. A single
  SQLite transaction creates tables, replaces rows, and commits together. Repeating
  an import never appends duplicates; removed source rows disappear on the next
  successful import. Validation or transaction failure preserves the prior snapshot.
  Header-only tables are allowed and explicitly report zero rows; a missing file fails.
- **Strict required fields:** malformed prices, quantities, IDs, dates, flags, JSON,
  statuses, duplicates, and broken relationships reject the import with file/row/field
  context, without customer values. No row is silently skipped and no missing price
  or stock is replaced with zero. Whitespace at field boundaries is trimmed.
  Optional descriptions, JSON specifications, customer contact fields, tracking,
  delivery estimates, and notes become SQL `NULL` when blank. No email uniqueness
  constraint is imposed; two supplied customer records share an email address.
- **Exact money:** `Decimal` converts inputs to integer cents. SQLite stores
  `price_cents` and `total_cents`; no binary floating point is used. A single valid
  active offer computes an effective price with half-up cent rounding. Price zero
  and stock zero are valid; negative or over-precision monetary amounts are rejected.
- **Availability:** only `status == active` and `stock_quantity > 0` qualifies. There
  are 61 available products. Product 96 is active with zero stock; 113 is discontinued
  with zero stock; 130 is `coming_soon` with stock 2; 136 is discontinued with stock 13.
  These source facts are preserved, and relevant anomalies produce import warnings.
- **Promotions:** only four records are active: 12 (product 127, 10%), 14 (121, 20%),
  19 (90, 18%), and 24 (94, 8%). There are no start/end dates. `is_active` is the sole
  supplied authority, representing the snapshot rather than verified live validity.
  Campaign names or the current month never activate an offer. Products 93, 96, and
  99 have multiple inactive offers. If future inputs contain multiple active offers
  for one product, all are returned with a warning and the base price remains in
  effect until clarified. Unavailable products are not offered a promotional price.
  Discounts are never stacked; PIX calculations are deferred. The policy states
  that its 5% PIX discount cannot be combined with promotional pricing (page 6).
- **Historical orders:** 12/20 lack tracking codes and delivery estimates; 16/20
  have empty notes. Missing optional fields remain unknown. Stored totals on orders
  3 and 20 differ from current catalog sums (3450.00 vs 3498.00; 1400.00 vs 1488.00).
  No historical unit price or discount is supplied, so totals are preserved without
  attributing a cause. Order status and payment method remain required source text;
  no speculative enum or automatic order-total reconciliation is applied.
- **Policy fidelity:** extraction collapses layout whitespace but preserves wording
  and physical pages. The manual (version 2.1, June 2025) lists different phone
  numbers on pages 1–2 and 6, and email spellings differ between pages 1 and 2.
  Payment conditions on page 3 have general and installment-specific minimums.
  Page 4 leaves shipping for an order of exactly BRL 500 unspecified, and its
  defect-exchange period must not be confused with the warranty period on page 7.
  Excerpts preserve these ambiguities. A future agent must cite the source and
  request staff clarification for conflicting/unspecified cases, rather than invent
  a unified rule.

## Verification

```sh
python -m pytest
python -m compileall -q src
```

Tests use only synthetic fixtures and temporary databases. They cover repeatable
imports, exact prices/stock, availability and effective-price filters, invalid or
missing data, atomic failure behavior, and policy excerpts with page references.
`tests/fixtures/build_policy_fixture.py` regenerates the synthetic PDF using only
the standard library.

The source-data CLI commands above require the original files. Windows execution
is verified during development; Linux execution has not been run in this workspace.
Verified with Python 3.13.15, pypdf 6.21.4, and pytest 9.2.0: **20 test cases passed**,
package compilation succeeded, and `pip check` reported no broken requirements.
The installed CLI imported the originals twice with unchanged row counts, returned
three available Yamaha products up to BRL 1000, read product 81 as BRL 599.90 with
12 units, calculated product 90's active 18% offer as BRL 1967.18 from BRL 2399.00,
retrieved `devolucao` from page 4, and exported all eight policy pages.

## Next steps

Choose an LLM/provider and add a small tool-calling loop around the existing catalog
and policy functions. Then implement the welcoming, informal, professional Portuguese
persona; grounded answers and conflict handling; out-of-scope redirection; and
three to five verified conversation examples. Add conversation tests for missing
products, unavailable stock, inactive promotions, and ambiguous policies.

There is currently no LLM client, tool orchestration, natural-language chat,
conversation memory, authentication, live inventory synchronization, semantic
retrieval, OCR, or delivery-status interface. Customer/order access requires a
deliberate identity and privacy design before exposing it through future tools.

## AI assistance

ChatGPT was used for planning this staged project, as reported by the project owner.
Codex was used for assisted implementation: reading the supplied materials,
auditing CSV relationships and edge cases, writing the Python modules and synthetic
fixtures, preparing documentation, and running/reviewing verification commands.
The application itself does not use ChatGPT, Codex, or another LLM at runtime yet.
