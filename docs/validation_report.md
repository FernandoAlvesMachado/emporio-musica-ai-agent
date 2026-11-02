# Challenge validation report

Validation date: 2026-11-02, America/Cuiaba.

## Revision and evidence scope

Final implementation analyzed: `929626ed37ec7d2d95f57e1428b5334e67e14186`
(`Handle Gemini outages with bounded requests and explicit errors`). Previous
real stages are `20ab1d4` (Gemini conversations and validated tools), `aac03f2`
(browser interface), and `226e11c` (data foundation). The task began on clean
`main` at `aac03f2`; its 30-test baseline passed. No history was rewritten.

The bounded retry/timeout and explicit outage-error fixes are included in that
final implementation commit. `git status --short --branch` then showed clean
application code, with only this report untracked: `?? docs/validation_report.md`.
This report records that code revision and awaits its own documentation commit;
no uncommitted application fixes or already-created report commit are implied.

The three-page challenge brief, six original CSVs, eight-page policy PDF, AGENTS,
README, code, and tests were inspected. Source correctness was checked against
CSV/PDF values independently of model replies. Deterministic checks, isolated
provider tests, local browser checks, and actual Gemini execution are distinct.
A provider double or mocked HTTP transport is never a real conversation.

Statuses are `PASS`, `FAIL`, `BLOCKED`, and `NOT_IMPLEMENTED`, scoped to the stated
evidence. Python, agent behavior, and delivery artifacts are mandatory. Provider,
framework, interface, persistent history, and using every file are choices or
optional improvements, as stated on pages 1-2 of the brief.

## Requirement matrix

| Requirement | Mandatory or optional | Status | Evidence | Remaining action |
| --- | --- | --- | --- | --- |
| Python as main language | Mandatory, brief p. 2 | PASS | `pyproject.toml`, `src/emporio_music/`; clean reproduction ran Python 3.13.15. | Python 3.11 is declared but not separately run; Linux is untested. |
| Conversational CLI implemented | CLI is the selected interface for the mandatory agent | PASS | `cli.py:run_chat`; `chat --help` lists options. Isolated agent tests exercise free input, source-backed turns, follow-ups, reset, and bounds. | Complete actual provider verification. |
| Native SDK serialization and tool-result contract | Provider/API are technical choices | PASS | `pytest tests/test_sdk_contract.py`: 1 passed using installed google-genai 2.34.0 and local `httpx.MockTransport`. | This test never contacted Google; verify external compatibility separately. |
| Real model-generated conversation | Mandatory for the functional chatbot | BLOCKED | Authenticated model list HTTP 200 versus unauthenticated HTTP 403; both model identifiers listed. Real generation returned 503/UNAVAILABLE or timed out; final bounded live scenario returned `model_timeout`. No chat text. | When generation availability is restored, execute and review the five genuine scenarios. |
| Store persona | Mandatory, brief p. 1 and policy p. 6 | BLOCKED | `prompts.py` specifies welcoming/informal/professional behavior; configuration and isolated tests are not live behavior evidence. | Review actual replies and follow-up turns. |
| Appropriate model routing between data and policies | Mandatory, brief p. 1 | BLOCKED | Agent/tool dispatch is implemented and isolated tests pass; real model routing is not verified. | Inspect actual tool traces and the original sources. |
| Out-of-scope handling | Mandatory, brief p. 1 | BLOCKED | Policy pp. 2/6 and system instructions define scope; live verifier contains the scenario. | Run/review real unrelated and accessory requests. |
| Original data and relationships preserved | Explicit user validation; all-file use is a choice | PASS | `validate_sources.py`: PASS; counts 9/65/25/50/20/22, unique keys, foreign keys, stored totals, and quantities independently checked. | Preserve original exclusions. |
| Reimport without duplicates | Explicit user validation | PASS | Source validator imported twice and checked exact counts; clean-environment verifier repeated the load. | None for the verified snapshot. |
| Money/quantity/stock/promotion conversion | Explicit user validation | PASS | Source validator compared every product price, stock, active offer, all item quantities, and stored order totals with direct CSV calculations. | None for these deterministic conversions. |
| Name/category, price, availability search | Explicit user validation | PASS | Source validator matched 12 category-5 products up to BRL 1000; category tests passed; actual browser filter returned 3 Yamaha results. | Verify model selection of category/filters. |
| Product details and promotions | Grounding requirement and explicit validation | PASS | All records source-compared: product 95 = 2199.00/stock 5; product 90 = 2399.00 base, active 18%, 1967.18 effective/stock 3. | Confirm actual model responses preserve these facts. |
| Unknown/unavailable/invalid/missing data | Explicit user validation | PASS | Full 62-test suite and source validator passed absent results, invalid sources/nulls, snapshot preservation, and status/stock cases; product 96 cannot be quoted for sale. | Review real model wording and alternatives. |
| Policy extraction, full pages, references | Explicit validation supporting grounding | PASS | Source validator: 8 pages; complete pages 2/3/4 matched direct PDF extraction; tool tests passed; actual browser search returned p. 4. | Cite retrieved pages in actual responses. |
| Exact payment and nonstacking calculations | Explicit user validation | PASS | Source validator: product 81 PIX 569.91; product 90 PIX 1967.18 without stacking; exact credit totals; unavailable product 96 ineligible. Payment tests passed. | Verify actual model use and explanation. |
| Return assessment and clarification | Grounding behavior and explicit validation | BLOCKED | Full text on pp. 4/7; prompt requires channel/date/condition clarification and prohibits return execution. | Review the genuine return dialogue. |
| Recognize missing/conflicting information | Explicit behavioral validation | BLOCKED | README records contact/installment/shipping ambiguities; quotation tool defers ambiguous credit cases. | Verify actual clarification replies. |
| Application source/instruction trust boundary | Explicit user validation | PASS | `test_source_instructions_are_not_promoted_to_system_messages` passed; tool data remains separate from system instructions; dispatch rejects arbitrary operations. | Actual model resistance is separately unverified. |
| Actual model resists source instructions | Explicit behavioral validation | BLOCKED | Structural/isolated checks cannot establish model compliance. | Perform a controlled real-model source-instruction check. |
| Unsupported store actions absent | Explicit user requirement | PASS | `tools.py` and dispatch tests: no order/refund/reservation/complaint/customer-lookup action is exposed. | Confirm actual replies never claim completed actions. |
| Explicit errors without simulation or leaks | Explicit user requirement | PASS | Agent/browser error tests passed; actual missing-key UI showed HTTP 503 setup error and no fake replies. Final SDK failures map to `provider_unavailable`/`model_timeout`; no successful reply is substituted. | Continue treating provider errors as failed execution. |
| Cross-turn context/reset/isolation/bounds | Optional project choice, tested if implemented | PASS | Isolated agent/HTTP tests and Chrome provider-double checks passed; memory is local and bounded. | Verify genuine model interpretation of references. |
| Persistent conversation history | Optional, brief p. 2 | NOT_IMPLEMENTED | Sessions are memory-only; interactions use `store=False`. | None required in selected scope. |
| Existing browser catalog/policies | Optional interface; existing UI validation requested | PASS | Actual application in Chrome: catalog 65, Yamaha filter 3, policy p. 4, mobile 390 without overflow/JavaScript errors; HTTP tests passed. | None for those non-model flows. |
| Browser chat UI/session orchestration | Optional interface; existing UI validation requested | PASS | Explicitly isolated Chrome provider double passed send/follow-up/reset/source/mobile flows; HTTP chat tests passed. | Not a Gemini conversation; verify configured provider separately. |
| Automated suite/static checks | Explicit user validation | PASS | Latest `pytest`: 62 passed in 2.91s, including two new outage/timeout cases; compilation, JavaScript syntax, and `pip check` passed. | Repeat affected checks only after changes. |
| Clean local installation/data/browser reproduction | Explicit user validation | PASS | Final `verify_installation.py`: fresh venv, editable install, copied originals, repeat load, 62 tests in 3.14s, HTTP 200/catalog 65, temporary cleanup. | None for the verified final local reproduction. |
| Real chat in reproduced environment | Explicit user validation | BLOCKED | Clean verifier deliberately omitted credentials and reported missing configuration explicitly. | Complete credentialed real E2E separately. |
| Packaged resources | Technical packaging choice | PASS | Wheel built; ZIP inspection found agent/tools/prompts and all 3 web assets, no `.env` or raw inputs. | None for inspected package. |
| Public GitHub visibility | Mandatory deliverable, brief p. 2 | PASS | GitHub `get_repo` returned public visibility for FernandoAlvesMachado/emporio-musica-ai-agent. | Published contents checked separately. |
| Deliverables published publicly | Mandatory deliverable | FAIL | GitHub size 0; `git ls-remote --heads origin` returned no heads, exit 0. No push requested/performed. | Obtain publication authorization, push real history normally, verify contents. |
| Genuine development history | Mandatory, brief p. 2 | PASS | `git log`: 226e11c, aac03f2, 20ab1d4, 929626e are separate actual working stages; none pushed yet. | Preserve history; no force-push/fabricated commits. |
| README setup/decisions/limitations | Mandatory, brief p. 2 | PASS | README covers exact setup/provider/start/test instructions; clean verifier reproduced local installation/data/startup. | Keep real-provider/publication limitations explicit. |
| Truthful AI assistance | Mandatory when used, brief p. 2 | PASS | README reports ChatGPT planning as stated by owner and Codex implementation/audit/testing; Gemini is the runtime provider. | Keep declaration truthful. |
| 3-5 genuine English conversations | Mandatory count; English requested by owner | BLOCKED | Examples README is a recording plan, not a transcript. No real conversations were generated or fabricated. | Record/source-review 3-5 actual conversations, including a nontrivial case. |
| No tracked credentials/private originals | Explicit user requirement | PASS | `check_tracked_files.py`: 43 implementation files passed bounded credential-pattern/private-input/database/log checks; `.env.example` key value was also asserted empty. | Include this report in final staged-file scan; not a universal secret guarantee. |
| Customer/order lookup | Optional source use | NOT_IMPLEMENTED | Imported locally; no model/browser lookup tools or routes. | Add identity/privacy design before exposing customer records. |
| Specific framework/hosting/vector database | Optional technical approaches | NOT_IMPLEMENTED | Small package, official SDK, SQLite, and `http.server`; no such service required. | None for chosen architecture. |
| Overall readiness | Mandatory overall outcome | BLOCKED | Actual model behavior, real examples, and public contents remain unestablished. | Complete these mandatory checks/deliverables before declaring readiness. |

## Executed verification

Commands below ran on Windows; `python` means `.venv\Scripts\python.exe`, except
the disposable interpreter created by the installation verifier. Versions:
Python 3.13.15, pypdf 6.21.4, google-genai 2.34.0, python-dotenv 1.2.4, pytest 9.2.0.
Python 3.11+ is declared support, not proof every version or Linux was executed.

```text
python -m pytest
python -m pytest tests/test_sdk_contract.py
python -m compileall -q src scripts
node --check src/emporio_music/web/app.js
python -m pip check
python scripts/validate_sources.py
python scripts/verify_installation.py
python scripts/check_tracked_files.py
```

Final application suite: **62 passed in 2.91s**, including two focused
outage/timeout cases. The native SDK contract separately returned **1 passed**,
explicitly isolated using local `httpx.MockTransport`. Compilation and JavaScript
syntax succeeded again after the final fixes; `pip check` found no broken
requirements. Final clean-environment reproduction installed the package, prepared
copied inputs, imported twice, repeated **62 tests in 3.14s**, and served HTTP 200
with catalog count 65. It deliberately omitted credentials, so its real-chat startup
was explicitly BLOCKED for that reason. This is separate from the configured
external-provider attempts below. Temporary inputs and environment were removed.

Source validation returned PASS, counts 9/65/25/50/20/22, 61 available products,
4 active promotions, 8 policy pages, and direct CSV/PDF agreement for all product
prices/stock/offers, order quantities/stored totals, relationships, reimport, and
category filtering. It also verified PIX 569.91 for product 81, PIX 1967.18 for
product 90 without stacking, exact installment totals, and product 96 ineligibility.

Chrome used the actual application for missing-key feedback, catalog/policy flows,
and mobile layout. Chat send/follow-up/reset checks used an explicitly isolated
provider double. No simulated output was counted as a Gemini response. An observed
Windows reset after rejected POSTs was fixed by draining their bounded bodies;
the complete suite passed after the fix. Screenshots and generated state are ignored.

## Genuine-provider execution status

The actual command was attempted:

```text
python scripts/validate_live.py --scenario 01-budget-recommendation
```

Initial probes stopped with `model_not_configured` before any external request.
After another local save, the key was detected. A subsequent model-list request
**with** the supplied key returned **HTTP 200**; the same request **without** it
returned **HTTP 403**. Both configured `gemini-3.8-flash` and the owner's
`gemini-flash-latest` alias appeared in the authenticated list. The key is accepted
for model listing and must not be called missing or invalid. Listing success does
not establish generation availability, quota, or successful conversations.

The actual native-SDK scenario made an external request and failed safely. A
minimal native-SDK request raised `InternalServerError`, status **503**, with no
certificate failure. A separate minimal GenerateContent request for configured
`gemini-3.8-flash` returned **HTTP 503**, provider status **UNAVAILABLE**. An explicit
diagnostic request using the alias from the owner's curl example timed out after
20 seconds with `TimeoutError` and no HTTP response. This was a deliberate diagnostic,
not an automatic application model fallback. A public Google API host probe had
also returned HTTP 404, independently establishing host reachability.

A final controlled invocation of the live scenario used the production client's
single-attempt retry policy with `EMPORIO_MODEL_TIMEOUT=15` in the child process.
It ended **BLOCKED**, reason **model_timeout**, with no response or examples. The
configured 503 case maps safely to `provider_unavailable`; timeout cases map to
`model_timeout`, with explicit browser feedback. The implementation converts the
configured timeout to SDK milliseconds and does not silently retry other models.

No actual assistant text or genuine conversation was recorded. All five required
live scenarios remain BLOCKED by external generation availability. Additional
external attempts are unnecessary while these service failures persist; they would
not establish factual correctness. The outage-handling fixes passed isolated tests;
a transient provider failure is not a PASS for runtime chat behavior or external
function-calling compatibility. No credential value was printed or recorded.

The live verifier covers budget recommendation/follow-up, existing/nonexistent
products, address/hours, return clarification/unsupported refund, and
scope/stock/nonstacking discounts. It records actual model responses only after
successful calls, keeps correctness pending independent review, and never silently
switches providers/models or substitutes scripted answers. Generated artifacts are
ignored under `data/processed/`; only genuine reviewed English conversations belong
in `examples/conversations/`.

## Independent source references

Category 5, Violões, contains 12 available products up to BRL 1000 in price order:
`83, 85, 89, 88, 81, 84, 87, 86, 107, 82, 91, 112`. None has an active promotion;
prices range from 429.90 to 999.00. A shorter recommendation can choose a subset,
but every suggestion must satisfy these original-source constraints.

Takamine GD20 is product 95: 2199.00, stock 5, active, no active promotion. Crafter
HT-100 is product 90: base 2399.00, stock 3, active 18%, effective 1967.18. Giannini
GF-3D is product 96: 799.90, stock 0, active but unavailable. IDs 113/130/136 remain
unavailable because of discontinued/coming-soon status even where stock is positive.
Promotion records have no validity dates.

Policy physical p. 2 gives Rua 14 de Maio, 3200 — Centro, Campo Grande–MS,
CEP 79202-333; Monday-Friday 09:00-18:00, Saturday 09:00-13:00, Sundays/holidays
closed. Payment is p. 3, returns p. 4, noncumulative/PIX rules p. 6. Full-page tools
fix the earlier omission of tables/conditions from short excerpts. No live calendar
is supplied; the agent must not invent holiday exceptions or reopening times.

Online regret returns: seven calendar days from receipt, original packaging,
unused, accessories/manuals, original-method refund within ten business days,
store-paid return freight (p. 4). An ambiguous request needs channel, receipt timing,
condition, and customization/final-sale facts. The application cannot approve a
return or issue a refund.

Phones differ between pp. 1-2 and 6, email spellings between pp. 1 and 2. Page 3
has general/detailed installment differences: quotations use explicit 4-6x/7-12x
minima and defer ambiguous <=3x installments below the general BRL 100 minimum to
staff. Exactly BRL 500 shipping is unspecified on p. 4. The 30-day defect exchange
and 90-day legal warranty remain distinct.

## Delivery disposition

**Not ready for delivery.** Data/tools, local reproduction, and isolated model/UI
orchestration have evidence. Actual model behavior, 3-5 genuine reviewed examples,
and public repository contents remain incomplete. No credential, customer data,
fabricated conversation, or simulated provider success was added to fill the gaps.
