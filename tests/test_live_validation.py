"""Isolated recorder tests; scripted replies are NOT real Gemini evidence."""

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from emporio_music.agent import AgentError
from emporio_music.config import Settings


SPEC = importlib.util.spec_from_file_location(
    "live_validation", Path(__file__).resolve().parents[1] / "scripts" / "validate_live.py",
)
live_validation = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(live_validation)


@pytest.fixture
def recorder(monkeypatch, tmp_path):
    raw = tmp_path / "raw"
    raw.mkdir()
    for table in ("categories", "products", "promotions"):
        (raw / f"supplied - {table}.csv").write_text(f"synthetic,{table}\n", encoding="utf-8")
    (raw / "customers.csv").write_text("private-must-not-be-fingerprinted", encoding="utf-8")
    manual = raw / "manual.pdf"
    manual.write_bytes(b"synthetic-manual-input")
    settings = Settings(raw, tmp_path / "database.sqlite3", manual, tmp_path)
    monkeypatch.setattr(live_validation, "Settings", SimpleNamespace(from_environment=lambda _: settings))
    monkeypatch.setattr(live_validation, "_git_revision", lambda: "a" * 40)

    class ScriptedSession:
        instances = []
        failure_on_turn = 2

        def __init__(self, settings, *, language):
            assert language == "en"
            self.configuration = SimpleNamespace(model="isolated-test-model")
            self.messages = []
            self.closed = False
            self.instances.append(self)

        def send(self, message):
            self.messages.append(message)
            if len(self.messages) == self.failure_on_turn:
                raise AgentError("private-sdk-key-and-request-body", "provider_unavailable")
            return SimpleNamespace(text="Isolated test response, not a real conversation.", tool_calls=[{"name": "search_products"}])

        def close(self):
            self.closed = True

    monkeypatch.setattr(live_validation, "ChatSession", ScriptedSession)
    return ScriptedSession, settings, tmp_path / "evidence"


def test_second_turn_failure_preserves_partial_first_turn_and_stops(recorder, capsys):
    session_class, settings, output = recorder
    assert live_validation.main(["--output", str(output), "--delay", "0"]) == 2
    run, = output.iterdir()
    record = json.loads((run / "01-budget-recommendation.json").read_text(encoding="utf-8"))
    summary = json.loads((run / "execution-summary.json").read_text(encoding="utf-8"))
    manifest = json.loads((run / "run-manifest.json").read_text(encoding="utf-8"))
    document = (run / "01-budget-recommendation.md").read_text(encoding="utf-8")
    assert record["execution"] == manifest["execution"] == summary[0]["execution"] == "BLOCKED"
    assert record["partial"] is True
    assert len(record["turns"]) == summary[0]["completed_turns"] == 1
    assert record["expected_turns"] == 2
    assert record["reason_code"] == "provider_unavailable"
    assert "PARTIAL EXECUTION" in document and "not a completed conversation" in document
    assert len(session_class.instances) == 1
    assert len(session_class.instances[0].messages) == 2
    assert session_class.instances[0].closed
    assert manifest["git_revision"] == "a" * 40
    assert set(manifest["source_snapshot"]) == {"categories", "products", "promotions", "manual"}
    assert manifest["source_snapshot"]["manual"]["sha256"] == hashlib.sha256(settings.policies_path.read_bytes()).hexdigest()
    for table in ("categories", "products", "promotions"):
        path = settings.raw_dir / f"supplied - {table}.csv"
        assert manifest["source_snapshot"][table]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert "private-sdk" not in capsys.readouterr().out
    assert all("private-sdk" not in path.read_text(encoding="utf-8") for path in run.iterdir())


def test_repeated_runs_never_overwrite_prior_evidence(recorder):
    session_class, _, output = recorder
    session_class.failure_on_turn = None
    arguments = ["--output", str(output), "--scenario", "01-budget-recommendation", "--delay", "0"]
    assert live_validation.main(arguments) == 0
    first_run, = output.iterdir()
    before = {path.name: path.read_bytes() for path in first_run.iterdir()}
    # Block a later run on its first turn, leaving the completed run untouched.
    session_class.failure_on_turn = 1
    assert live_validation.main(arguments) == 2
    assert len(list(output.iterdir())) == 2
    assert {path.name: path.read_bytes() for path in first_run.iterdir()} == before
    complete = json.loads((first_run / "01-budget-recommendation.json").read_text(encoding="utf-8"))
    assert complete["execution"] == "completed" and complete["partial"] is False
    assert len(complete["turns"]) == complete["expected_turns"] == 2
