from datetime import UTC, datetime, timedelta, timezone

from app.schemas import SyncRunRead


def _run(started_at: datetime) -> dict:
    return {
        "id": "run-1",
        "mode": "fixture",
        "from_date": None,
        "to_date": None,
        "started_at": started_at,
        "finished_at": None,
        "status": "SUCCEEDED",
        "documents_seen": 0,
        "documents_created": 0,
        "documents_updated": 0,
        "documents_unchanged": 0,
        "documents_failed": 0,
        "reconciliation_warnings": 0,
        "error_summary": None,
    }


def test_naive_stored_timestamp_is_sent_as_utc():
    # SQLite returns this naive; without an offset a browser would read it as local time.
    body = SyncRunRead.model_validate(_run(datetime(2026, 9, 9, 8, 34, 45))).model_dump(mode="json")

    assert body["started_at"] == "2026-09-09T08:34:45Z"
    assert body["finished_at"] is None


def test_aware_timestamp_keeps_its_offset():
    hanoi = timezone(timedelta(hours=7))
    started = datetime(2026, 9, 9, 15, 34, 45, tzinfo=hanoi)

    run = SyncRunRead.model_validate(_run(started))

    assert run.started_at == started
    assert run.started_at.astimezone(UTC).hour == 8
