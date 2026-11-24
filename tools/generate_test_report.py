import platform
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT_DIRECTORY = ROOT / "reports" / "tests"


def _status(case: ElementTree.Element) -> str:
    for status in ("failure", "error", "skipped"):
        if case.find(status) is not None:
            return status
    return "passed"


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        junit_path = Path(directory) / "junit.xml"
        command = [sys.executable, "-m", "pytest", "-q", f"--junitxml={junit_path}"]
        exit_code = subprocess.run(command, cwd=ROOT, check=False).returncode
        tree = ElementTree.parse(junit_path)
    suite = tree.getroot().find("testsuite")
    if suite is None:
        raise RuntimeError("pytest did not produce a test suite")
    suite.attrib.pop("hostname", None)
    suite.attrib.pop("timestamp", None)
    for case in suite.iter("testcase"):
        case.attrib.pop("time", None)
    statuses = [_status(case) for case in suite.iter("testcase")]
    counts = {name: statuses.count(name) for name in ("passed", "failure", "error", "skipped")}
    REPORT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    tree.write(REPORT_DIRECTORY / "junit.xml", encoding="utf-8", xml_declaration=True)
    lines = [
        "# Test Report",
        "",
        f"- Generated (UTC): {datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Python: {platform.python_version()} ({platform.python_implementation()})",
        f"- Operating system: {platform.system()}",
        f"- pytest: {version('pytest')}",
        f"- hypothesis: {version('hypothesis')}",
        "- Command: `uv run --locked python tools/generate_test_report.py`",
        f"- Pytest exit code: {exit_code}",
        "",
        "| Total | Passed | Failed | Errors | Skipped |",
        "| ---: | ---: | ---: | ---: | ---: |",
        f"| {len(statuses)} | {counts['passed']} | {counts['failure']} "
        f"| {counts['error']} | {counts['skipped']} |",
        "",
        "Per-test results are in `junit.xml` in this directory.",
        "",
    ]
    (REPORT_DIRECTORY / "test-report.md").write_text("\n".join(lines), encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
