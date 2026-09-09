"""Operational exceptions: where the order flow and the accounting record disagree.

Read-only. Every category is a question the office would ask, and every answer
carries the rows behind it rather than a number to be taken on trust.
"""

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import read_access
from app.database import get_db
from app.schemas import ExceptionReportRead
from app.services import exceptions_view

router = APIRouter(prefix="/operations", tags=["operations"], dependencies=[read_access])


@router.get("/exceptions", response_model=ExceptionReportRead)
async def exceptions(
    as_of: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500, description="Rows listed per category"),
    session: Session = Depends(get_db),
):
    report = exceptions_view.report(session, as_of=as_of, limit=limit)
    return ExceptionReportRead(
        as_of=report.as_of,
        total=report.total,
        groups=[
            {"category": group.category, "count": group.count, "items": group.items}
            for group in report.groups
        ],
    )
