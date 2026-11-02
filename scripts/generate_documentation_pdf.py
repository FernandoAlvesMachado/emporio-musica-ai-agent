"""Render current repository Markdown into an optional English documentation PDF.

This is a documentation snapshot, never a replacement for validation evidence.
Only the standard library is used for Markdown/HTML; PDF export optionally uses
Playwright. Install it separately with ``python -m pip install playwright`` and
``python -m playwright install chromium``. An installed Chrome can instead be
selected with ``--browser-channel chrome``. No application dependency is added.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PDF = ROOT / "docs/Emporio_da_Musica_AI_Agent_Documentacao.pdf"
SOURCE_PATHS = (
    "README.md",
    "docs/validation_report.md",
    "examples/conversations/README.md",
)
_INLINE = re.compile(r"`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|\*([^*]+)\*")
_SEPARATOR = re.compile(r"^:?-{3,}:?$")


def inline_markup(text: str) -> str:
    """Escape raw HTML and render the small inline subset used by our docs."""
    fragments = []
    cursor = 0
    for match in _INLINE.finditer(text):
        fragments.append(html.escape(text[cursor:match.start()]))
        code, label, target, strong, emphasis = match.groups()
        if code is not None:
            fragments.append(f"<code>{html.escape(code)}</code>")
        elif label is not None:
            target = target.strip()
            if urlsplit(target).scheme in {"", "https", "http"}:
                fragments.append(f'<a href="{html.escape(target, quote=True)}">{html.escape(label)}</a>')
            else:
                fragments.append(html.escape(label))
        elif strong is not None:
            fragments.append(f"<strong>{html.escape(strong)}</strong>")
        else:
            fragments.append(f"<em>{html.escape(emphasis or '')}</em>")
        cursor = match.end()
    fragments.append(html.escape(text[cursor:]))
    return "".join(fragments)


def table_cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def markdown_to_html(markdown: str) -> str:
    """Render headings, paragraphs, lists, fenced code and GFM-style tables.

    This deliberately small renderer does not execute embedded HTML or fetch URLs.
    Unsupported Markdown remains readable escaped text.
    """
    lines = markdown.splitlines()
    output = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        fence = re.match(r"^\s*(`{3,}|~{3,})", line)
        if fence:
            marker = fence.group(1)
            code = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith(marker):
                code.append(lines[index])
                index += 1
            output.append("<pre><code>" + html.escape("\n".join(code)) + "</code></pre>")
            index += 1
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            level = len(heading.group(1))
            output.append(f"<h{level}>{inline_markup(heading.group(2))}</h{level}>")
            index += 1
            continue
        if "|" in line and index + 1 < len(lines):
            separators = table_cells(lines[index + 1])
            if separators and all(_SEPARATOR.fullmatch(cell) for cell in separators):
                headers = table_cells(line)
                output.append("<table><thead><tr>" + "".join(f"<th>{inline_markup(cell)}</th>" for cell in headers) + "</tr></thead><tbody>")
                index += 2
                while index < len(lines) and "|" in lines[index] and lines[index].strip():
                    cells = table_cells(lines[index])
                    output.append("<tr>" + "".join(f"<td>{inline_markup(cell)}</td>" for cell in cells) + "</tr>")
                    index += 1
                output.append("</tbody></table>")
                continue
        item = re.match(r"^(\s*)([-+*]|\d+[.)])\s+(.+)$", line)
        if item:
            ordered = item.group(2)[0].isdigit()
            tag = "ol" if ordered else "ul"
            output.append(f"<{tag}>")
            while index < len(lines):
                item = re.match(r"^(\s*)([-+*]|\d+[.)])\s+(.+)$", lines[index])
                if not item or item.group(2)[0].isdigit() != ordered:
                    break
                content = [item.group(3)]
                index += 1
                while index < len(lines) and lines[index].startswith("  ") and lines[index].strip() and not re.match(r"^\s*([-+*]|\d+[.)])\s+", lines[index]):
                    content.append(lines[index].strip())
                    index += 1
                output.append("<li>" + inline_markup(" ".join(content)) + "</li>")
            output.append(f"</{tag}>")
            continue
        paragraph = [stripped]
        index += 1
        while index < len(lines) and lines[index].strip():
            if re.match(r"^\s*(#{1,6}\s|`{3,}|~{3,}|[-+*]\s|\d+[.)]\s)", lines[index]):
                break
            if "|" in lines[index] and index + 1 < len(lines) and all(_SEPARATOR.fullmatch(cell) for cell in table_cells(lines[index + 1])):
                break
            paragraph.append(lines[index].strip())
            index += 1
        output.append("<p>" + inline_markup(" ".join(paragraph)) + "</p>")
    return "\n".join(output)


def build_document(sources: list[tuple[str, bytes]]) -> str:
    """Preserve current source claims and provenance rather than invent a summary."""
    sections = []
    provenance = []
    for name, raw in sources:
        digest = hashlib.sha256(raw).hexdigest()
        provenance.append(f"<tr><td>{html.escape(name)}</td><td><code>{digest}</code></td></tr>")
        sections.append(f'<section><p class="source">Source: {html.escape(name)}</p>' + markdown_to_html(raw.decode("utf-8-sig")) + "</section>")
    return """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'">
<title>Emporio da Musica AI Agent - Documentation and Validation Evidence</title>
<style>
@page { size: A4; }
* { box-sizing: border-box; }
body { color: #173d37; font-family: Arial, sans-serif; font-size: 9pt; line-height: 1.5; }
h1,h2,h3,h4,h5,h6 { color: #173d37; break-after: avoid; line-height: 1.25; }
h1 { font-size: 22pt; border-bottom: 2px solid #d8ded4; padding-bottom: 8pt; }
h2 { font-size: 15pt; margin-top: 20pt; }
h3 { font-size: 12pt; }
p { margin: 0 0 8pt; }
a { color: #245c50; overflow-wrap: anywhere; }
code { font-family: Consolas, monospace; font-size: 8pt; overflow-wrap: anywhere; }
pre { background: #f1f3ed; border: 1px solid #d8ded4; padding: 9pt; white-space: pre-wrap; overflow-wrap: anywhere; }
pre code { font-size: 7.5pt; }
table { border-collapse: collapse; width: 100%; margin: 10pt 0; table-layout: fixed; font-size: 7pt; }
th,td { border: 1px solid #cdd8d1; padding: 5pt; text-align: left; vertical-align: top; overflow-wrap: anywhere; }
th { background: #e8eee7; }
thead { display: table-header-group; }
tr { break-inside: avoid; }
li { margin-bottom: 4pt; }
.source { color: #58685e; font-size: 8pt; }
section { break-before: page; }
.notice { border-left: 3pt solid #cd714f; background: #fbf3ed; padding: 10pt; }
</style></head><body>
<h1>Emporio da Musica AI Agent</h1>
<h2>Documentation and validation evidence</h2>
<p class="notice">This PDF is an optional snapshot of the current repository Markdown.
It is not evidence that a real-model call succeeded or that delivery is ready.
The validation report below records actual results, source evidence and remaining
blockers. A recording plan is not a genuine conversation transcript.</p>
<p>Source files and SHA-256 hashes at generation time:</p>
<table><thead><tr><th>Source</th><th>SHA-256</th></tr></thead><tbody>""" + "".join(provenance) + "</tbody></table>" + "\n".join(sections) + "</body></html>"


def generate_pdf(browser_channel: str | None = None) -> Path:
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError:
        raise SystemExit("Optional PDF export needs Playwright. Run: python -m pip install playwright; then python -m playwright install chromium. This is not a chatbot runtime dependency.") from None
    sources = []
    for name in SOURCE_PATHS:
        source = (ROOT / name).resolve()
        if not source.is_relative_to(ROOT):
            raise SystemExit("Documentation sources must remain inside the repository.")
        sources.append((name, source.read_bytes()))
    destination = OUTPUT_PDF.resolve()
    if not destination.is_relative_to(ROOT) or not destination.parent.is_dir():
        raise SystemExit("The documentation PDF destination must remain inside the repository docs directory.")
    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.launch(**({"channel": browser_channel} if browser_channel else {}))
        except Error:
            raise SystemExit("No usable PDF browser was found. Run: python -m playwright install chromium; or use --browser-channel chrome with installed Google Chrome.") from None
        try:
            page = browser.new_page()
            page.route("**/*", lambda route: route.abort())
            page.set_content(build_document(sources), wait_until="domcontentloaded")
            pdf_bytes = page.pdf(
                format="A4", print_background=True, display_header_footer=True,
                header_template='<div style="font:8px Arial;color:#666;margin-left:15mm">Emporio da Musica AI Agent - documentation snapshot</div>',
                footer_template='<div style="font:8px Arial;color:#666;width:100%;text-align:center">Page <span class="pageNumber"></span> of <span class="totalPages"></span></div>',
                margin={"top":"18mm", "bottom":"18mm", "left":"15mm", "right":"15mm"},
            )
        finally:
            browser.close()
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".pdf", delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(pdf_bytes)
    try:
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Saved documentation snapshot: {destination.relative_to(ROOT)} ({len(pdf_bytes)} bytes)")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--browser-channel", choices=("chrome", "msedge"), help="Use an installed Chrome/Edge instead of Playwright Chromium.")
    args = parser.parse_args()
    generate_pdf(args.browser_channel)


if __name__ == "__main__":
    main()
