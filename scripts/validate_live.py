"""Record actual Gemini conversations for later review; never simulate a provider."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=[name for name, _ in SCENARIOS], help="Run one scenario rather than all five.")
    parser.add_argument("--output", type=Path, default=ROOT / "data/processed/live-validation")
    parser.add_argument("--delay", type=float, default=2, help="Seconds between turns; no automatic provider/model fallback.")
    args = parser.parse_args()
    if not 0 <= args.delay <= 30:
        parser.error("Delay must be between zero and thirty seconds.")
    args.output.mkdir(parents=True, exist_ok=True)
    settings = Settings.from_environment(ROOT)
    results = []
    for name, messages in SCENARIOS:
        if args.scenario and name != args.scenario:
            continue
        session = None
        try:
            session = ChatSession(settings, language="en")
            turns = []
            for message in messages:
                reply = session.send(message)
                turns.append({"user": message, "assistant": reply.text, "tool_calls": reply.tool_calls})
                if args.delay:
                    time.sleep(args.delay)
            timestamp = datetime.now(timezone.utc).isoformat()
            record = {"scenario": name, "model": session.configuration.model, "provider": "gemini", "executed_at_utc": timestamp, "turns": turns, "review": "PENDING independent source review; execution alone is not behavioral correctness"}
            (args.output / f"{name}.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            document = [f"# {name}\n", f"Provider: Gemini. Model: `{record['model']}`. Executed: {timestamp}.\n", "Actual model transcript. Correctness review is pending; do not treat this file as a verified example yet.\n"]
            for turn in turns:
                document.extend(["## Customer\n", turn["user"] + "\n", "## Assistant\n", turn["assistant"] + "\n", "Tools actually executed: " + ", ".join(call["name"] for call in turn["tool_calls"]) + ".\n"])
            (args.output / f"{name}.md").write_text("\n".join(document), encoding="utf-8")
            results.append({"scenario": name, "execution": "completed", "correctness": "pending_review"})
            print(f"Recorded genuine Gemini conversation: {name}; correctness review pending.", flush=True)
        except AgentError as error:
            results.append({"scenario": name, "status": "BLOCKED", "reason_code": error.code, "reason": str(error)})
            print(f"BLOCKED {name}: {error.code}: {error}", flush=True)
            break
        finally:
            if session is not None:
                session.close()
    (args.output / "execution-summary.json").write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    return 2 if any(result.get("status") == "BLOCKED" for result in results) else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
