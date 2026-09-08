from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path

from app.config import get_settings
from app.database import SessionLocal
from app.integrations.easybooks.client import EasyBooksClient, HttpxReadOnlyTransport
from app.integrations.easybooks.sync import FixtureBundle, fetch_live_bundle, sync_bundle


def _date(value: str) -> date:
    return date.fromisoformat(value)


def main() -> None:
    parser = argparse.ArgumentParser(prog="uniops")
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync = subparsers.add_parser("sync-easybooks", help="run read-only EasyBooks ingestion")
    mode = sync.add_mutually_exclusive_group(required=True)
    mode.add_argument("--fixture", type=Path)
    mode.add_argument("--live", action="store_true")
    sync.add_argument("--from-date", type=_date)
    sync.add_argument("--to-date", type=_date)
    args = parser.parse_args()

    settings = get_settings()
    to_date = args.to_date or date.today()
    from_date = args.from_date or (to_date - timedelta(days=settings.easybooks_sync_overlap_days))
    if args.fixture:
        payload = json.loads(args.fixture.read_text())
        bundle = FixtureBundle.from_dict(payload)
        mode_name = "fixture"
    else:
        transport = HttpxReadOnlyTransport(settings)
        client = EasyBooksClient(transport, settings)
        bundle = fetch_live_bundle(client, from_date, to_date)
        mode_name = "live"

    with SessionLocal() as session:
        run = sync_bundle(session, bundle, mode=mode_name, from_date=from_date, to_date=to_date)
        print(
            json.dumps(
                {
                    "sync_run_id": run.id,
                    "status": run.status.value,
                    "documents_seen": run.documents_seen,
                    "created": run.documents_created,
                    "updated": run.documents_updated,
                    "unchanged": run.documents_unchanged,
                    "failed": run.documents_failed,
                    "reconciliation_warnings": run.reconciliation_warnings,
                }
            )
        )


if __name__ == "__main__":
    main()
