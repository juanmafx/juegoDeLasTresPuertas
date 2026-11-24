#!/bin/sh
# Runs the unit tests (plain and sanitized) and the shared conformance suite, then writes c/reports/.
set -eu
cd "$(dirname "$0")/.."
mkdir -p reports
plain=$(./build/test-runner 2>&1) && plain_code=0 || plain_code=$?
sanitized=$(./build/test-runner-sanitize 2>&1) && sanitized_code=0 || sanitized_code=$?
conformance=$(python3 -I ../tools/conformance.py --cli "$(pwd)/build/monty-lab" \
    --report reports/conformance.json 2>&1) && conformance_code=0 || conformance_code=$?
sanitized_conformance=$(python3 -I ../tools/conformance.py \
    --cli "$(pwd)/build/monty-lab-sanitize" 2>&1) && sanitized_conformance_code=0 \
    || sanitized_conformance_code=$?
python3 -I - "$(pwd)/reports/conformance.json" <<'PY'
import json, sys
path = sys.argv[1]
data = json.load(open(path, encoding="utf-8"))
data["cli"] = "c/build/monty-lab"
open(path, "w", encoding="utf-8").write(json.dumps(data, indent=2) + "\n")
PY
{
    echo "# C Test Report"
    echo
    echo "- Generated (UTC): $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "- Compiler: $(${CC:-gcc} --version | head -n 1)"
    echo "- Python running tools/conformance.py: $(python3 --version 2>&1)"
    echo "- Operating system: $(uname -s) $(uname -m)"
    echo "- Command: \`make report\` (runs \`tools/report.sh\`)"
    echo
    echo "| Run | Exit code | Summary |"
    echo "| --- | ---: | --- |"
    echo "| Unit tests, plain build | $plain_code | $(printf '%s\n' "$plain" | tail -n 1) |"
    echo "| Unit tests, AddressSanitizer + UBSan | $sanitized_code | $(printf '%s\n' "$sanitized" | tail -n 1) |"
    echo "| Conformance, plain CLI | $conformance_code | see below |"
    echo "| Conformance, sanitized CLI | $sanitized_conformance_code | see below |"
    echo
    echo "## Unit tests, plain build"
    echo
    echo '```text'
    printf '%s\n' "$plain"
    echo '```'
    echo
    echo "## Unit tests, AddressSanitizer + UBSan"
    echo
    echo '```text'
    printf '%s\n' "$sanitized"
    echo '```'
    echo
    echo "## tools/conformance.py against build/monty-lab"
    echo
    echo '```text'
    printf '%s\n' "$conformance"
    echo '```'
    echo
    echo "The JSON report of this run is in \`conformance.json\`."
    echo
    echo "## tools/conformance.py against build/monty-lab-sanitize"
    echo
    echo '```text'
    printf '%s\n' "$sanitized_conformance"
    echo '```'
} > reports/test-report.md
echo "wrote reports/test-report.md"
test "$plain_code" -eq 0 && test "$sanitized_code" -eq 0 && test "$conformance_code" -eq 0 \
    && test "$sanitized_conformance_code" -eq 0
