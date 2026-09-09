"""Read-only analytics over the accounting layer.

No write operation exists here and none should. Any signed-in role may read,
matching the existing rule that reading is what `factory-read` is for.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import read_access
from app.database import get_db
from app.schemas import CommercialOverviewRead, PurchaseSummaryRead, SalesSummaryRead
from app.services import analytics

router = APIRouter(prefix="/analytics", tags=["analytics"], dependencies=[read_access])

FromDate = Query(default=None, description="First business date to include, inclusive")
ToDate = Query(default=None, description="Last business date to include, inclusive")


def _window(from_date: date | None, to_date: date | None) -> None:
    """Refuse an inverted window before any query runs."""
    try:
        analytics.check_window(from_date, to_date)
    except analytics.InvalidDateWindow as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc


@router.get("/overview", response_model=CommercialOverviewRead)
async def overview(
    from_date: date | None = FromDate,
    to_date: date | None = ToDate,
    session: Session = Depends(get_db),
):
    _window(from_date, to_date)
    return analytics.overview(session, from_date, to_date)


@router.get("/sales", response_model=SalesSummaryRead)
async def sales(
    from_date: date | None = FromDate,
    to_date: date | None = ToDate,
    session: Session = Depends(get_db),
):
    _window(from_date, to_date)
    return analytics.sales_summary(session, from_date, to_date)


@router.get("/purchases", response_model=PurchaseSummaryRead)
async def purchases(
    from_date: date | None = FromDate,
    to_date: date | None = ToDate,
    session: Session = Depends(get_db),
):
    _window(from_date, to_date)
    return analytics.purchase_summary(session, from_date, to_date)
