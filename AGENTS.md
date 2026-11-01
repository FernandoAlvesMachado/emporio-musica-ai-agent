# Emporio da Musica AI Agent

This repository implements the Artefact AI Engineer challenge in stages. Read
`docs/reference/` and inspect the supplied local `data/raw/` files before changing
data assumptions. The implemented foundation is a deterministic Python application
with terminal commands and a local browser interface. LLM integration, persona,
conversation routing, and conversation examples are pending.

## Conventions

- Communicate with the project owner in Portuguese. Write code, identifiers,
  documentation, and commit messages in English. Browser interface text is Portuguese.
- Use a small `src/emporio_music/` package, Python 3.11+, `pathlib`, SQLite,
  parameterized queries, integer cents, and `Decimal` for monetary conversions.
- Preserve original inputs. Validate imports before replacing a database snapshot;
  never invent missing prices, stock, discounts, or policy rules.
- Availability requires `status == "active"` and positive stock. Promotion dates
  are absent; use the supplied active flag and never stack discounts.
- Keep personal customer data, original supplied materials, generated databases,
  extracted policies, credentials, logs, and environments out of Git. Tests use
  only synthetic fixtures. Never include customer values in validation errors.
- Preserve physical PDF page numbers and identify policy excerpts as source text.
  Conflicting policy passages require clarification, not silent correction.
- Keep the browser server bound to `127.0.0.1` for local development. Reuse the
  existing catalog/import/policy functions. Serve only packaged browser assets and
  explicit application endpoints, never raw source files or customer/order records.
- Check Git status before edits. Preserve existing work; do not rewrite history or
  force-push. Commit only verified work with the configured Git identity.

## Verification

Run these commands from the repository root after installing the package:

```text
python -m pytest
python -m pytest tests/test_browser.py
python -m compileall -q src
python -m emporio_music --help
python -m emporio_music serve --help
python -m emporio_music load
python -m emporio_music search Yamaha --max-price 1000 --available
python -m emporio_music product 81
python -m emporio_music policies devolucao
```

On Windows without environment activation, replace `python` with
`.venv\Scripts\python.exe`. On Linux use `.venv/bin/python`.
The final four commands need the supplied files, which must remain local.

For manual browser verification, run `python -m emporio_music serve --open-browser`.
Keep the terminal open, test catalog filters/details and policy page references at
`http://127.0.0.1:8000`, and stop the server with `Ctrl+C`. The page can import the
configured source CSVs through its import button; server startup does not import
automatically. Use `--port 8001` if the default port is occupied.
