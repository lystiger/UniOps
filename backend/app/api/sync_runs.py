from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import read_access
from app.database import get_db
from app.schemas import SyncRunRead
from app.services import sync_runs

router = APIRouter(prefix="/sync-runs", tags=["observability"])


@router.get("", response_model=list[SyncRunRead], dependencies=[read_access])
async def list_sync_runs(
    limit: int = Query(default=20, ge=1, le=200),
    session: Session = Depends(get_db),
):
    """Read-only ingestion history. UniOps never writes back to EasyBooks."""
    return sync_runs.list_sync_runs(session, limit)
