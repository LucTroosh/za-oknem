"""Export the FastAPI OpenAPI schema to packages/api-contract/openapi.json (TASK-2.1,
ADR-024). Deterministic (sorted keys, fixed indent, trailing newline), so a diff means a
real contract change.

    uv run python scripts/export_openapi.py          # rewrite the committed file
    uv run python scripts/export_openapi.py --check  # CI: fail when it is out of date
"""

import json
import sys
from importlib.metadata import version
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
TARGET = API_DIR.parents[1] / "packages" / "api-contract" / "openapi.json"
GENERATED = Path("/tmp/openapi.generated.json")  # uploaded by CI when --check fails

sys.path.insert(0, str(API_DIR))

from app.main import app  # noqa: E402  (needs API_DIR on sys.path)


def render() -> str:
    return json.dumps(app.openapi(), indent=2, sort_keys=True, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        if not TARGET.exists() or TARGET.read_text(encoding="utf-8") != text:
            GENERATED.write_text(text, encoding="utf-8")
            sys.exit(
                f"{TARGET} is out of date - run: uv run python scripts/export_openapi.py "
                f"(fastapi {version('fastapi')}, pydantic {version('pydantic')}: with no uv.lock "
                "a dependency release can change the serialization too)"
            )
    else:
        TARGET.write_text(text, encoding="utf-8")
