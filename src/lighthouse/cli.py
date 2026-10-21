import json
import sys
from datetime import datetime, timezone

from src.lighthouse.reconcile import run_tick
from src.lighthouse.schedule import load_schedule
from src.lighthouse.service import lighthouse_service


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args != ["tick"]:
        print("usage: python -m src.lighthouse.cli tick", file=sys.stderr)
        return 2
    result = run_tick(lighthouse_service, load_schedule(), datetime.now(timezone.utc))
    print(json.dumps(result))
    return 1 if result.get("action") == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
