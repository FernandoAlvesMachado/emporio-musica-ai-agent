"""Bounded checks for common credential patterns and accidentally tracked inputs."""

import re
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = [
    re.compile(rb"AIza[0-9A-Za-z_-]{35}"),
    re.compile(rb"sk-(?:proj-)?[A-Za-z0-9_-]{32,}"),
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
]


def main() -> None:
    result = subprocess.run(
        ["git", "-c", f"safe.directory={ROOT.as_posix()}", "ls-files", "-z"],
        cwd=ROOT, capture_output=True, check=True,
    )
    names = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
    findings = []
    for name in names:
        path = Path(name)
        private_name = path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example")
        original_input = path.parts[:2] in {("data", "raw"), ("docs", "reference")} and path.name != ".gitkeep"
        generated = path.suffix.lower() in {".db", ".sqlite", ".sqlite3", ".log"}
        if private_name or original_input or generated:
            findings.append(name)
        content = (ROOT / path).read_bytes()
        if any(pattern.search(content) for pattern in PATTERNS):
            findings.append(name)
    if findings:
        # Print locations only; never print the matching credential text.
        raise SystemExit("FAIL: inspect tracked file locations: " + ", ".join(sorted(set(findings))))
    print(f"PASS: {len(names)} tracked files checked; no common credential patterns, private .env, original inputs, databases or logs found.")
    print("Scope: bounded filename/pattern checks, not a universal secret-detection guarantee.")


if __name__ == "__main__":
    main()
