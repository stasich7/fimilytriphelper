from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

CURRENT_FILE = Path(__file__).resolve()
REPO_ROOT = CURRENT_FILE.parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agents.hotel_search.models import SearchRequest
from agents.hotel_search.orchestrator import run_search


def main() -> int:
    parser = argparse.ArgumentParser(description="Run hotel search agent")
    parser.add_argument("--input", required=True, help="Path to input JSON file")
    parser.add_argument("--json-out", required=True, help="Path to output JSON file")
    parser.add_argument("--md-out", required=True, help="Path to output markdown file")
    args = parser.parse_args()

    request = load_request(Path(args.input))
    payload, markdown = run_search(request)

    json_out = Path(args.json_out)
    md_out = Path(args.md_out)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_out.write_text(markdown, encoding="utf-8")
    return 0


def load_request(path: Path) -> SearchRequest:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return SearchRequest.from_dict(raw)


if __name__ == "__main__":
    raise SystemExit(main())
