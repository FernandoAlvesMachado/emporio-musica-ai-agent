"""Record actual Gemini conversations for later review; never simulate a provider."""

import argparse
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from emporio_music.agent import AgentError, ChatSession
from emporio_music.config import Settings


ROOT = Path(__file__).resolve().parents[1]
SCENARIOS = [
    ("01-budget-recommendation", [
        "Please recommend three available acoustic guitars costing at most BRL 1000. Give the actual prices and product IDs.",
        "What is the recorded stock of the first option, and how much would I pay by PIX?",
    ]),
    ("02-product-and-missing-item", [
        "How much is the Takamine GD20, and is it available?",
        "Do you also sell a Quantum Nebula ZX-9999 guitar?",
    ]),
    ("03-address-and-hours", [
        "What is the store's address and its opening hours on weekdays, Saturdays and Sundays?",
    ]),
    ("04-return-clarification", [
        "I regret buying my instrument. Can I return it?",
        "I bought it online and received it three days ago. It is unused, in the original packaging with all manuals and accessories, with no customization or final-sale notice. Can you issue my refund now?",
    ]),
    ("05-scope-stock-and-discounts", [
        "Can you forecast tomorrow's weather and recommend a guitar cable?",
        "Is the Giannini GF-3D available? Can I combine the Crafter HT-100 active promotion with another five percent PIX discount?",
    ]),
]


SAFE_FAILURES = {
    "model_not_configured": "A local Gemini API key has not been configured.",
    "model_timeout": "The Gemini request timed out.",
    "rate_limited": "The Gemini quota or rate limit was reached.",
    "provider_access_denied": "Gemini rejected access to the configured project.",
    "model_unavailable": "The configured Gemini model is unavailable.",
    "provider_unavailable": "The Gemini provider is temporarily unavailable.",
    "empty_response": "Gemini did not produce a source-backed answer.",
    "incomplete_response": "Gemini did not complete the answer.",
    "tool_limit": "The bounded tool-call limit was reached.",
    "session_limit": "The bounded session-turn limit was reached.",
    "session_closed": "The conversational session has ended.",
    "invalid_request": "The conversational request or configuration is invalid.",
    "model_error": "The Gemini request failed; check connectivity and provider configuration.",
}


def _write_json(path: Path, value: object) -> None:
    """Keep the last complete checkpoint if a process stops during a later write."""
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _source_snapshot(settings: Settings) -> dict:
    """Fingerprint only the public catalog inputs and manual, never customer data."""
    def fingerprint(path: Path) -> dict:
        try:
            digest = hashlib.sha256()
            size = 0
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
                    size += len(chunk)
            return {"status": "available", "filename": path.name, "sha256": digest.hexdigest(), "size_bytes": size}
        except OSError:
            return {"status": "unavailable"}

    snapshot = {}
    for table in ("categories", "products", "promotions"):
        candidates = [path for path in settings.raw_dir.glob("*.csv") if path.stem == table or path.stem.endswith(" - " + table)]
        snapshot[table] = fingerprint(candidates[0]) if len(candidates) == 1 else {
            "status": "missing" if not candidates else "ambiguous",
        }
    snapshot["manual"] = fingerprint(settings.policies_path)
    return snapshot


def _git_revision() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True,
            timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{40,64}", revision) else None


def _write_conversation(directory: Path, record: dict) -> None:
    _write_json(directory / f"{record['scenario']}.json", record)
    completed = record["execution"] == "completed"
    document = [
        f"# {record['scenario']}\n",
        f"Provider: Gemini. Model: `{record['model']}`. Started: {record['executed_at_utc']}.\n",
        f"Execution: {record['execution']}. Completed turns: {len(record['turns'])}/{record['expected_turns']}.\n",
        "Actual model transcript. Correctness review is pending; execution alone does not verify behavior.\n"
        if completed else "PARTIAL EXECUTION: this is not a completed conversation or a delivery example.\n",
    ]
    if record.get("reason"):
        document.append(f"Blocking reason: {record['reason_code']}: {record['reason']}\n")
    for turn in record["turns"]:
        document.extend([
            "## Customer\n", turn["user"] + "\n", "## Assistant\n", turn["assistant"] + "\n",
            "Tools actually executed: " + ", ".join(call["name"] for call in turn["tool_calls"]) + ".\n",
        ])
    (directory / f"{record['scenario']}.md").write_text("\n".join(document), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=[name for name, _ in SCENARIOS], help="Run one scenario rather than all five.")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/live-validation", help="Evidence root; each invocation creates a unique run subdirectory.")
    parser.add_argument("--delay", type=float, default=2, help="Seconds between turns; no automatic provider/model fallback.")
    args = parser.parse_args(argv)
    if not 0 <= args.delay <= 30:
        parser.error("Delay must be between zero and thirty seconds.")
    args.output.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ") + "-" + uuid4().hex[:8]
    run_directory = args.output / run_id
    run_directory.mkdir(exist_ok=False)
    settings = Settings.from_environment(ROOT)
    manifest = {
        "run_id": run_id, "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "execution": "running", "git_revision": _git_revision(),
        "source_snapshot": _source_snapshot(settings),
        "selected_scenarios": [name for name, _ in SCENARIOS if not args.scenario or args.scenario == name],
        "review": "PENDING independent source review; execution alone is not behavioral correctness",
    }
    _write_json(run_directory / "run-manifest.json", manifest)
    print(f"Validation run directory: {run_directory}", flush=True)
    results = []
    for name, messages in SCENARIOS:
        if args.scenario and name != args.scenario:
            continue
        session = None
        record = {
            "scenario": name, "run_id": run_id, "run_manifest": "run-manifest.json",
            "model": None, "provider": "gemini", "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "execution": "running", "partial": True, "expected_turns": len(messages), "turns": [],
            "review": "NOT REVIEWED: partial execution is not a completed delivery example",
        }
        try:
            session = ChatSession(settings, language="en")
            record["model"] = session.configuration.model
            _write_conversation(run_directory, record)
            for message in messages:
                reply = session.send(message)
                record["turns"].append({"user": message, "assistant": reply.text, "tool_calls": reply.tool_calls})
                _write_conversation(run_directory, record)
                if args.delay:
                    time.sleep(args.delay)
            record.update(execution="completed", partial=False, review=manifest["review"])
            results.append({"scenario": name, "execution": "completed", "completed_turns": len(record["turns"]), "correctness": "pending_review"})
            print(f"Recorded genuine Gemini conversation: {name}; correctness review pending.", flush=True)
        except AgentError as error:
            # Do not serialize exceptions, which may acquire private provider details later.
            code = error.code if error.code in SAFE_FAILURES else "model_error"
            record.update(execution="BLOCKED", reason_code=code, reason=SAFE_FAILURES[code])
            results.append({
                "scenario": name, "execution": "BLOCKED", "status": "BLOCKED",
                "completed_turns": len(record["turns"]), "correctness": "not_reviewed_partial",
                "reason_code": code, "reason": SAFE_FAILURES[code],
            })
            print(f"BLOCKED {name}: {code}: {SAFE_FAILURES[code]}", flush=True)
        finally:
            record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
            _write_conversation(run_directory, record)
            _write_json(run_directory / "execution-summary.json", results)
            if session is not None:
                session.close()
        if record["execution"] == "BLOCKED":
            break
    blocked = any(result["execution"] == "BLOCKED" for result in results)
    manifest.update(execution="BLOCKED" if blocked else "completed", finished_at_utc=datetime.now(timezone.utc).isoformat())
    _write_json(run_directory / "run-manifest.json", manifest)
    return 2 if blocked else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
