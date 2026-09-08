from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EasyBooksSyncRun


def list_sync_runs(session: Session, limit: int = 20) -> list[EasyBooksSyncRun]:
    statement = select(EasyBooksSyncRun).order_by(EasyBooksSyncRun.started_at.desc()).limit(limit)
    return list(session.scalars(statement))
