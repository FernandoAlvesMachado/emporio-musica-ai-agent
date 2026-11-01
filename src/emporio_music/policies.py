"""Extract and search the supplied policy PDF with physical page references."""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from emporio_music.text import normalize_text


class PolicyError(ValueError):
    """The policy source cannot provide reliable searchable text."""


@dataclass(frozen=True)
class PolicyPage:
    page: int
    text: str


@dataclass(frozen=True)
class PolicyMatch:
    page: int
    text: str
    source: str


def extract_policy_pages(pdf_path: Path) -> list[PolicyPage]:
    """Read every physical page, rejecting missing text instead of hiding it."""
    pdf_path = Path(pdf_path)
    if not pdf_path.is_file():
        raise PolicyError(f"Policy PDF not found: {pdf_path}")
    try:
        with pdf_path.open("rb") as stream:
            reader = PdfReader(stream)
            if reader.is_encrypted:
                raise PolicyError("Encrypted policy PDFs are not supported.")
            if not reader.pages:
                raise PolicyError("The policy PDF contains no pages.")
            pages = []
            for number, page in enumerate(reader.pages, start=1):
                text = " ".join((page.extract_text() or "").split())
                if not text:
                    raise PolicyError(
                        f"Policy PDF page {number} has no extractable text; "
                        "OCR is not implemented."
                    )
                pages.append(PolicyPage(page=number, text=text))
            return pages
    except PolicyError:
        raise
    except (OSError, PyPdfError, ValueError, KeyError, TypeError) as error:
        raise PolicyError(f"Cannot extract policy PDF: {pdf_path.name}") from error


def _snippet(text: str, terms: set[str], max_chars: int = 900) -> str:
    """Return original-text windows containing every matched query term."""
    positions: dict[str, tuple[int, int]] = {}
    for match in re.finditer(r"[\w\u0300-\u036f]+", text):
        normalized = normalize_text(match.group())
        if normalized in terms and normalized not in positions:
            positions[normalized] = match.span()
    spans = sorted(positions.values())
    term_length = sum(end - start for start, end in spans)
    context = min(120, max(0, (max_chars - term_length - 5 * len(spans)) // (2 * len(spans))))
    windows: list[tuple[int, int]] = []
    for start, end in spans:
        start, end = max(0, start - context), min(len(text), end + context)
        if windows and start <= windows[-1][1]:
            windows[-1] = (windows[-1][0], max(end, windows[-1][1]))
        else:
            windows.append((start, end))
    pieces = [text[start:end].strip() for start, end in windows]
    snippet = " ... ".join(pieces)
    if windows[0][0] > 0:
        snippet = "... " + snippet
    if windows[-1][1] < len(text):
        snippet += " ..."
    return snippet


def search_policies(pdf_path: Path, query: str, limit: int = 5) -> list[PolicyMatch]:
    """Match all query words on a page, ignoring case and diacritics."""
    if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
        raise ValueError("Policy result limit must be a positive integer.")
    if len(query) > 200:
        raise ValueError("Policy queries must contain at most 200 characters.")
    terms = set(re.findall(r"\w+", normalize_text(query)))
    if not terms:
        raise ValueError("Policy query must contain at least one word or number.")
    matches = []
    for page in extract_policy_pages(pdf_path):
        tokens = Counter(re.findall(r"\w+", normalize_text(page.text)))
        if terms <= tokens.keys():
            score = sum(tokens[term] for term in terms)
            matches.append((score, page))
    matches.sort(key=lambda item: (-item[0], item[1].page))
    return [
        PolicyMatch(page=page.page, text=_snippet(page.text, terms), source=Path(pdf_path).name)
        for _, page in matches[:limit]
    ]


def export_policy_pages(pdf_path: Path, output_path: Path) -> int:
    """Write extracted text and 1-based page references to a UTF-8 JSON file."""
    pdf_path, output_path = Path(pdf_path), Path(output_path)
    if pdf_path.resolve() == output_path.resolve():
        raise PolicyError("The extraction output must differ from the original PDF.")
    if output_path.suffix.lower() != ".json":
        raise PolicyError("Policy extraction output must use the .json extension to protect source files.")
    pages = extract_policy_pages(pdf_path)
    payload = {"source": pdf_path.name, "pages": [asdict(page) for page in pages]}
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except OSError as error:
        raise PolicyError(f"Cannot write policy extraction: {output_path}") from error
    return len(pages)
