"""Reproduce installation and local startup in a disposable clean environment."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import venv
from pathlib import Path
from urllib.request import ProxyHandler, build_opener


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="emporio-clean-install-") as directory:
        temporary = Path(directory).resolve()
        # Every generated file and cleanup target belongs to this named temporary root.
        assert temporary.parent == Path(tempfile.gettempdir()).resolve()
        assert temporary.name.startswith("emporio-clean-install-")
        environment = temporary / "venv"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        project = temporary / "project"
        raw = project / "data/raw"
        raw.mkdir(parents=True)
        from emporio_music.config import Settings

        source = Settings.from_environment(ROOT)
        for path in source.raw_dir.iterdir():
            if path.suffix.lower() in {".csv", ".pdf"} and path.is_file():
                shutil.copy2(path, raw / path.name)
        if source.policies_path.parent.resolve() != source.raw_dir.resolve():
            shutil.copy2(source.policies_path, raw / source.policies_path.name)
        clean_environment = {
            key: value for key, value in os.environ.items()
            if not key.startswith("EMPORIO_") and key not in {"GEMINI_API_KEY", "GEMINI_MODEL", "GOOGLE_API_KEY", "PYTHONPATH"}
        }
        # Keep credentials out of the reproduction test; external E2E is a separate command.
        clean_environment.update({"PYTHONIOENCODING": "utf-8", "GEMINI_API_KEY": "", "EMPORIO_POLICIES_PATH": str(raw / source.policies_path.name)})

        def run(*arguments, input_text=None):
            return subprocess.run(
                [str(python), *arguments], cwd=project, env=clean_environment,
                input=input_text, text=True, encoding="utf-8", capture_output=True,
                timeout=180,
            )

        installation = run("-m", "pip", "install", "--disable-pip-version-check", "-e", f"{ROOT}[dev]")
        if installation.returncode:
            raise RuntimeError("Clean environment package installation failed. Check dependency/network access.")
        loaded = run("-m", "emporio_music", "load")
        assert loaded.returncode == 0, loaded.stderr
        counts = json.loads(loaded.stdout)["counts"]
        repeat = run("-m", "emporio_music", "load")
        assert repeat.returncode == 0 and json.loads(repeat.stdout)["counts"] == counts
        tests = run("-m", "pytest", str(ROOT / "tests"))
        assert tests.returncode == 0, tests.stdout + tests.stderr
        chat = run("-m", "emporio_music", "chat", input_text="/exit\n")
        assert chat.returncode != 0 and "GEMINI_API_KEY" in chat.stderr
        process = subprocess.Popen(
            [str(python), "-m", "emporio_music", "serve", "--port", "0"],
            cwd=project, env=clean_environment, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
        )
        try:
            line = process.stdout.readline().strip()
            assert line.startswith("Local browser interface: http://127.0.0.1:"), line
            url = line.removeprefix("Local browser interface: ")
            opener = build_opener(ProxyHandler({}))
            with opener.open(url, timeout=5) as response:
                assert response.status == 200 and "Empório" in response.read().decode("utf-8")
            with opener.open(url + "/api/status", timeout=5) as response:
                assert json.load(response)["product_count"] == counts["products"]
        finally:
            process.terminate()
            process.communicate(timeout=10)
        print(json.dumps({
            "installation": "PASS", "input_preparation": "PASS", "counts": counts,
            "repeat_import": "PASS", "tests": tests.stdout.strip(),
            "browser_startup": "PASS", "real_chat": "BLOCKED",
            "real_chat_reason": "No credential supplied to clean reproduction; validate_live.py performs external checks separately.",
            "cleanup": "Disposable virtual environment and copied inputs removed on exit.",
        }, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
