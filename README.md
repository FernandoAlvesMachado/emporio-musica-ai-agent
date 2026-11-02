# Emporio da Musica AI Agent

Python customer-service assistant for the Artefact AI Engineer challenge and a
fictional musical-instrument store in Campo Grande, Brazil.

The data foundation provides validated SQLite imports, catalog queries, PDF policy
retrieval with page references, and a local browser interface. The chatbot
integration uses Google's Gemini API, a conversational terminal interface, and
bounded, nonpersistent conversation context. Implementation and verification are
tracked separately; a working data query is not proof of a functioning AI agent.

**Real-model verification is currently BLOCKED by external provider failures.**
A key is now present locally;
the configured-model probe returned HTTP 503/UNAVAILABLE and the explicitly tested
AI Studio alias timed out. Isolated tests and deterministic source checks do not prove that
the external integration works. No real conversation transcripts are claimed.
See [the validation report](docs/validation_report.md) for evidence and remaining
delivery requirements.

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
`.venv/bin/python` on Linux in place of `python`. Runtime dependencies are `pypdf`,
the official `google-genai` SDK, and `python-dotenv`. CSV, SQLite, orchestration,
CLI, and the local HTTP server use the standard library. Tests use `pytest`.
Catalog/policy queries work without a model credential; conversational responses
require a Gemini API key and network access.

## Configure and start a conversation

Create a local configuration file from the supplied example if `.env` does not
already exist. Edit an existing `.env` instead of replacing it.

Windows PowerShell:

```powershell
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Linux/macOS:

```sh
[ -f .env ] || cp .env.example .env
```

Add your Gemini API key to `.env` as `GEMINI_API_KEY=...`; do not paste it into chat,
commit it, or include it in execution evidence. Obtain a key from
[Google AI Studio](https://aistudio.google.com/apikey). Google Gemini was selected
at the project owner's request. The default model is `gemini-3.8-flash`;
`GEMINI_MODEL` can select another compatible model available to your account.
The `gemini-flash-latest` identifier shown in the AI Studio example is also accepted
through `GEMINI_MODEL`. It is an alias whose target may change; this project never
silently switches the model you configure.
Google's [pricing documentation](https://ai.google.dev/gemini-api/docs/pricing)
describes free-tier eligibility and quotas. A free tier does not guarantee unlimited
requests, access for every account, or availability of every model.

Prepare the supplied data and start the conversational CLI:

```sh
python -m emporio_music load
python -m emporio_music chat
```

On Windows without environment activation:

```powershell
.\.venv\Scripts\python.exe -m emporio_music load
.\.venv\Scripts\python.exe -m emporio_music chat
```

Enter free-form questions and continue in the same session. Use `/reset` to clear
the current session and `/exit` to finish. EOF or `Ctrl+C` also ends the CLI.
The default response language is Brazilian Portuguese. For English delivery
recordings, run `python -m emporio_music chat --language en`. Add `--show-tools` to
display tool names used during a CLI session without exposing credentials or
customer records.

The agent calls allowlisted catalog, policy, and payment-quotation tools when
facts are needed. The model generates the conversational response; the application
does not silently substitute fixed or simulated replies after a provider error.
Without a key, or when the provider rejects a request, an explicit configuration
or provider error is shown. A failed call is not a successful chatbot demonstration.

The [official function-calling guide](https://ai.google.dev/gemini-api/docs/function-calling)
is the implementation reference. A manual tool loop keeps model decisions visible
in application code and avoids introducing an agent framework. API interactions
use `store=False`; session context is held locally in memory, not persisted as
conversation files. This setting does not replace Google's applicable service and
data-processing terms.

## Local browser interface

From the repository root, run:

```sh
python -m emporio_music serve --open-browser
```

On Windows without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m emporio_music serve --open-browser
```

Keep this terminal open while testing. The command opens
`http://127.0.0.1:8000` in the default browser. If it does not open automatically,
open that address manually. Stop the server with `Ctrl+C`. If port 8000 is already
in use, run `python -m emporio_music serve --port 8001 --open-browser` and use the
address printed in the terminal.

The Portuguese interface provides a conversation area as well as catalog cards,
name/maximum-price/availability filters, product details, promotion information,
catalog counters, and policy excerpts with PDF page references. Chat requires the
same Gemini configuration as the CLI; its real-model behavior must be verified
separately from the deterministic catalog and policy controls.

Catalog controls call the same data functions as the terminal commands. Their
literal name field is distinct from the conversational input; try `Yamaha`, a
maximum price of `1000`, and available products. Chat can use category tools for
requests such as acoustic guitars within a budget.

The server reads the configured SQLite snapshot and policy PDF. Starting it does
not import data automatically: use the import button in the page or run the `load`
command first. The button validates and imports all six configured source CSVs,
just like the CLI. Existing catalog data is preserved if an import fails. The
browser uses the same environment variables and `--root` configuration as the CLI.

This is a local development interface bound only to `127.0.0.1`, not a hosted or
production service. It exposes catalog and policy operations; customer/order
records and raw source files have no browser endpoints. No external frontend
framework, CDN, or hosting service is required. A model account is needed only for
chat. Browser conversations use isolated, bounded in-memory sessions; restarting
the application discards them.

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
interfaces expose only catalog and policy queries. The SQLite database contains personal
customer data and must remain local. Do not commit it or publish raw inputs.

## Configuration

Defaults are relative to the working directory. Use `pathlib` paths on either
Windows or Linux. `.env.example` documents the following environment variables:

| Variable | Default |
| --- | --- |
| `EMPORIO_PROJECT_ROOT` | `.` |
| `EMPORIO_RAW_DIR` | `data/raw` |
| `EMPORIO_DATABASE_PATH` | `data/processed/emporio.sqlite3` |
| `EMPORIO_POLICIES_PATH` | `data/raw/políticas_da_loja.pdf` |
| `GEMINI_API_KEY` | No default; required for chat |
| `GEMINI_MODEL` | `gemini-3.8-flash` |
| `EMPORIO_CHAT_LANGUAGE` | `pt-BR` |
| `EMPORIO_MODEL_TIMEOUT` | `45` seconds |
| `EMPORIO_MAX_TOOL_ROUNDS` | `6` |
| `EMPORIO_MAX_TURNS` | `20` |

Absolute paths are accepted. Relative data paths resolve against the project root.
`--root PATH` overrides `EMPORIO_PROJECT_ROOT` and must precede the subcommand.
The project-root `.env` is loaded automatically. Variables already set in the
process environment take precedence over `.env`. Do not rely on activation of a
virtual environment to supply credentials. `--language en` overrides the default
chat language for that CLI session. Limits bound model/tool iterations and session
growth; they do not establish a provider spending cap.

## Development commands

```sh
python -m emporio_music --help
python -m emporio_music chat --help
python -m emporio_music load
python -m emporio_music search Yamaha --max-price 1000 --available
python -m emporio_music search --unavailable
python -m emporio_music product 81
python -m emporio_music product 90
python -m emporio_music policies devolucao
python -m emporio_music policies "promocoes cumulativas"
python -m emporio_music extract-policies
```

The installed `emporio` command provides the same interface. One-shot data commands
return JSON on stdout; `serve` prints its local URL and keeps running until stopped;
`chat` starts the conversational loop. Catalog queries read SQLite rather than
hardcoded responses. Re-run `load`
after updating inputs. Policy search reads the configured PDF directly.

`search` matches a literal name fragment, ignoring case and accents. `%` and `_`
are literal characters, not SQL wildcards. `--max-price` uses a decimal point and
filters the **effective price**, inclusively. Results sort by effective price and
product ID; default limit is 20 (`--limit N`). Omitting the availability flag shows
all statuses. `--available` and `--unavailable` are mutually exclusive.
Literal name matching has no category inference or stemming. Original guitar names
contain brands/models rather than the word `violao`; use `Yamaha` for the one-shot
name-search demonstration. The chatbot can list categories and filter category 5,
`Violões`, instead of guessing a product-name match.

Details include source stock/status/specifications, base price, effective price,
and active promotion records. BRL amounts are exact two-decimal strings. A missing
product exits with status 1; invalid data/configuration exits with status 2.
Empty search results are `[]`, never invented alternatives.

`policies` requires every query word on the same page, ignores case/accents, and
returns bounded original-text excerpts, source filename, and physical page number
(starting at 1, including the cover). It ranks matching pages by query-word count,
then page number. It does not expand synonyms or resolve conflicting rules.
The chatbot can also retrieve full policy pages. This is necessary for topics
such as opening hours and payment conditions, where a short lexical excerpt may
omit a table or qualifying rule. Retrieved text remains source material, not an
instruction source that can override the agent's system prompt.
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
  agent.py        # Gemini interaction and bounded conversational tool loop
  prompts.py      # Persona, grounding, scope, and source trust instructions
  tools.py        # Allowlisted catalog, policy, and payment tools
  data.py         # CSV validation, schema, atomic snapshot import
  catalog.py      # Parameterized SQLite searches and product details
  policies.py     # PDF extraction, page references, lexical retrieval
  text.py         # Shared accent/case normalization
  cli.py          # Conversational CLI and deterministic development commands
  browser.py      # Loopback-only HTTP server using the existing data functions
  web/            # Packaged HTML, CSS, and JavaScript for the local interface
data/raw/         # Local unchanged source files (ignored)
data/processed/   # Generated SQLite and extracted JSON (ignored)
docs/reference/   # Local challenge brief (ignored)
examples/conversations/  # Real delivery transcripts, once external runs succeed
docs/validation_report.md # Requirement status, evidence, and remaining actions
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
  modules handle orchestration. A small `http.server` adapter serves packaged browser
  assets and calls the existing Python functions. No agent framework, external web
  framework, vector database, infrastructure service, or generic repository
  abstraction is needed. The official Gemini SDK supplies the provider adapter;
  the application owns the tool loop and keeps ordinary SQL out of model control.
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
  Discounts are never stacked. The payment-quotation tool keeps monetary arithmetic
  outside the model. It consults product data and relevant policy pages before
  quoting payment conditions. PIX receives 5% off the table price only when no
  product promotion applies; PIX does not reduce an already promotional price.
  For credit, detailed page-3 conditions take precedence over its general summary:
  4–6 installments require at least BRL 80 each; 7–12 require BRL 100. The ambiguous
  <=3x exception is not silently converted into a new rule: proposed installments
  below the general BRL 100 minimum need staff clarification before approval.
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
  Excerpts preserve these ambiguities. The agent must cite the source and
  request staff clarification for conflicting/unspecified cases, rather than invent
  a unified rule.

## Requirement boundaries

The mandatory challenge features are a Python customer-service text agent,
store-aligned persona, source-grounded replies, data/policy routing, and suitable
out-of-scope behavior. Required deliverables are a public Git repository with
real development history, this README, and three to five real conversation examples,
including a nontrivial data or policy scenario.

SQLite, the `src/` layout, Gemini, manual function calling, bounded in-memory
context, all-six-CSV import, and the local browser UI are project choices. Persistent
history, a web interface, a particular framework, and use of every supplied file
are not mandatory in the original brief. No customer/order lookup is offered;
this avoids exposing another customer's records without an identity design.

## Verification

```sh
python -m pytest
python -m pytest tests/test_browser.py
python -m compileall -q src
python -m emporio_music serve --help
python -m emporio_music chat --help
```

Tests use only synthetic fixtures and temporary databases. They cover repeatable
imports, exact prices/stock, availability and effective-price filters, invalid or
missing data, atomic failure behavior, and policy excerpts with page references.
Browser integration tests make real HTTP requests to a temporary loopback server
with synthetic inputs. They cover imports, catalog filters/details, policy page
references, missing sources, rejected invalid requests, and source-file privacy.
`tests/fixtures/build_policy_fixture.py` regenerates the synthetic PDF using only
the standard library.

The source-data CLI commands above require the original files. Windows execution
is verified during development; Linux execution has not been run in this workspace.
The chatbot implementation was verified with Python 3.13.15, pypdf 6.21.4,
google-genai 2.34.0, python-dotenv 1.2.4, and pytest 9.2.0: **62 test cases passed**.
These include scripted-provider, native-SDK mocked HTTP, and browser-session tests;
none calls Gemini. A clean temporary virtual environment also installed the package,
loaded/reimported all original inputs, passed all tests, and served the browser
interface successfully. Chat startup in that credential-free environment explicitly
reported missing configuration. Python compilation, JavaScript syntax, and
`pip check` passed. The original 30-test baseline is recorded in the validation report.
The installed CLI imported the originals twice with unchanged row counts, returned
three available Yamaha products up to BRL 1000, read product 81 as BRL 599.90 with
12 units, calculated product 90's active 18% offer as BRL 1967.18 from BRL 2399.00,
retrieved `devolucao` from page 4, and exported all eight policy pages.
The browser interface was exercised in the installed Chrome through Playwright:
initial catalog loading, price/availability filters, product details, empty results,
policy page references, reimport, and first-run database creation all passed.
Desktop and 390-pixel mobile layouts were checked with no horizontal overflow or
browser JavaScript errors. Playwright was used only for development verification;
it is not an application dependency or a requirement for running the HTTP tests.

Provider-mocked tests are isolated tests. They can verify orchestration, argument
validation, source trust handling, and session isolation, but they cannot establish
real model availability, answer quality, or external function-calling compatibility.
The browser chat was also exercised in Chrome using an explicitly isolated provider
double: sending, follow-up context, reset, source references, and the 390-pixel layout
passed without JavaScript errors. This is UI evidence, not a real Gemini conversation.
The native SDK test validates serialization against a local mocked HTTP transport;
it does not prove external availability or model behavior.

## Remaining delivery work and limitations

Configure a valid Gemini key and run the required real-model scenarios: available
guitars within a budget; an existing product's price/stock; address or opening hours;
a return request that needs clarification; and out-of-scope/nonexistent-product
questions. Compare every factual answer with the original CSV/PDF, not with a prior
chatbot answer. Record three to five genuine conversations in English using
`chat --language en`; prompts listed in the examples directory are a test plan,
not transcripts or substitute evidence.

For repeatable source checks and genuine conversation recording:

```sh
python scripts/validate_sources.py
python scripts/verify_installation.py
python scripts/validate_live.py
```

`validate_sources.py` compares all source prices, stock, quantities, active offers,
and relationships with the application, using a temporary database and expectations
calculated directly from the CSVs/PDF. `verify_installation.py` creates a temporary
clean virtual environment, installs the package, prepares copied inputs, runs tests,
and checks browser startup. It deliberately omits credentials; the separate live
command is responsible for provider access. All temporary copies are removed.

`validate_live.py` makes real Gemini calls in English for five scenarios, saving
actual responses and tool evidence under the ignored `data/processed/live-validation/`.
It never substitutes simulated output and stops with `BLOCKED` on missing access.
Use `--scenario 01-budget-recommendation` to run one scenario. Successful execution
alone is not correctness: compare the transcript with the independent source values
in `docs/validation_report.md` before adding a reviewed example to the delivery folder.

External verification and real transcripts remain blocked until a provider call
succeeds. The configured key was accepted for model listing (HTTP 200, compared
with HTTP 403 without a key). Actual generation returned HTTP 503/UNAVAILABLE or
timed out; neither the configured model nor the explicitly tested AI Studio alias
produced a conversation. Provider requests now use one SDK attempt and the
configured per-request timeout, with explicit unavailable/timeout errors and no
automatic model fallback. The public GitHub repository is visible, but its content was still empty
when audited; local commits alone do not publish it. The project is not ready for
delivery while those mandatory checks and deliverables remain outstanding.

There is no persistent conversation history, customer authentication, live inventory
synchronization, semantic retrieval, OCR, order-status interface, or action execution
such as placing orders, processing returns, reserving stock, or issuing refunds.
The agent must not promise these operations. Prompt instructions reduce the risk of
ungrounded answers or source-instruction injection; actual behavior still requires
real-model tests. Linux execution has not been verified in this workspace.

## AI assistance

ChatGPT was used for planning this staged project, as reported by the project owner.
Codex was used for assisted implementation: reading the supplied materials,
auditing CSV relationships and edge cases, writing the Python modules and synthetic
fixtures, adding the local browser and Gemini chatbot integrations, preparing
documentation, and running/reviewing verification commands. Tests with provider
substitutes are identified as isolated tests. The selected runtime model is Gemini;
ChatGPT and Codex were development assistance, not runtime providers.
