# Shared JSON output for experiment scripts.
import json
import sys
from pathlib import Path
from typing import Any


def emit(document: dict[str, Any], out: Path | None) -> None:
    text = json.dumps(document, indent=2) + "\n"
    if out is None:
        sys.stdout.write(text)
        return
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)
