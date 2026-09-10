from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import admin_access, current_user
from app.config import Settings, get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import User
from app.schemas import LoginRequest, PasswordChange, UserRead
from app.services import auth

router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["auth"])


def _set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=settings.session_lifetime_hours * 3600,
        path="/",
        httponly=True,
        # Lax keeps the cookie off cross-site POST/PATCH/DELETE requests, which
        # is what stands in for a CSRF token here.
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


@router.post("/login", response_model=UserRead)
async def login(
    data: LoginRequest,
    response: Response,
    session: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        user = auth.authenticate(session, data.username, data.password)
    except auth.AuthError as exc:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            code=getattr(exc, "code", "INVALID_CREDENTIALS"),
            params=getattr(exc, "params", {}),
        ) from exc
    issued = auth.start_session(session, user, settings.session_lifetime_hours)
    _set_session_cookie(response, settings, issued.token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, response: Response, session: Session = Depends(get_db)):
    settings = get_settings()
    auth.revoke_session(session, request.cookies.get(settings.session_cookie_name, ""))
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
    )


@router.get("/me", response_model=UserRead)
async def me(user: User = Depends(current_user)):
    return user


@router.post("/change-password", response_model=UserRead)
async def change_password(
    data: PasswordChange,
    response: Response,
    user: User = Depends(current_user),
    session: Session = Depends(get_db),
):
    settings = get_settings()
    try:
        auth.authenticate(session, user.username, data.current_password)
    except auth.AuthError as exc:
        raise ApiError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="current password is not correct",
            code="INVALID_CURRENT_PASSWORD",
        ) from exc
    try:
        updated = auth.set_password(session, user.username, data.new_password)
    except auth.WeakPassword as exc:
        raise ApiError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
            code=getattr(exc, "code", "WEAK_PASSWORD"),
            params=getattr(exc, "params", {}),
        ) from exc
    # set_password ends every session for the account, including this browser's.
    # Issuing a fresh one keeps the person who just changed their own password
    # signed in while still signing out everywhere else.
    issued = auth.start_session(session, updated, settings.session_lifetime_hours)
    _set_session_cookie(response, settings, issued.token)
    return updated


@users_router.get("", response_model=list[UserRead], dependencies=[admin_access])
async def list_users(session: Session = Depends(get_db)):
    """Read-only account list. Accounts are created and changed from the CLI."""
    return auth.list_users(session)
