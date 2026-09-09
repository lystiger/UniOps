"""User accounts and sign-in sessions.

UniOps has three roles. `ADMIN` may do everything including account
administration, `OFFICE` may read and write orders and catalog, and
`FACTORY_READ` may only read. Accounts are created from the CLI rather than a
web form: there is no self-registration and no public account surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, UserRole, UserSession
from app.security import (
    MIN_PASSWORD_LENGTH,
    as_utc,
    hash_password,
    hash_session_token,
    needs_rehash,
    new_session_token,
    spend_dummy_verification,
    verify_password,
)

# A session row is only touched again once its last_seen_at is this stale, so a
# busy board does not write to the database on every poll.
LAST_SEEN_REFRESH = timedelta(minutes=5)

ROLE_BY_CLI_NAME = {
    "admin": UserRole.ADMIN,
    "office": UserRole.OFFICE,
    "factory-read": UserRole.FACTORY_READ,
}


class AuthError(Exception):
    """The credential or session presented cannot be accepted."""


class UserExists(Exception):
    pass


class UserNotFound(Exception):
    pass


class WeakPassword(Exception):
    pass


@dataclass(frozen=True)
class IssuedSession:
    """A started session plus the raw cookie value, which is never stored."""

    token: str
    expires_at: datetime


def normalize_username(username: str) -> str:
    return username.strip().lower()


def _require_strong(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise WeakPassword(f"password must be at least {MIN_PASSWORD_LENGTH} characters")


def get_user(session: Session, username: str) -> User | None:
    return session.scalar(select(User).where(User.username == normalize_username(username)))


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.username)))


def create_user(
    session: Session,
    *,
    username: str,
    password: str,
    role: UserRole,
    full_name: str | None = None,
) -> User:
    name = normalize_username(username)
    if not name:
        raise UserNotFound("username is required")
    _require_strong(password)
    if get_user(session, name) is not None:
        raise UserExists(f"user {name} already exists")
    user = User(
        username=name,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        is_active=True,
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


def set_password(session: Session, username: str, password: str) -> User:
    _require_strong(password)
    user = get_user(session, username)
    if user is None:
        raise UserNotFound(f"user {normalize_username(username)} does not exist")
    user.password_hash = hash_password(password)
    # A password change ends every signed-in browser for that account. That is
    # the point of changing it after a suspected leak.
    revoke_all_sessions(session, user)
    session.commit()
    session.refresh(user)
    return user


def set_active(session: Session, username: str, active: bool) -> User:
    user = get_user(session, username)
    if user is None:
        raise UserNotFound(f"user {normalize_username(username)} does not exist")
    user.is_active = active
    if not active:
        revoke_all_sessions(session, user)
    session.commit()
    session.refresh(user)
    return user


def authenticate(session: Session, username: str, password: str) -> User:
    user = get_user(session, username)
    if user is None:
        spend_dummy_verification()
        raise AuthError("username or password is not correct")
    if not verify_password(user.password_hash, password):
        raise AuthError("username or password is not correct")
    if not user.is_active:
        # Reported separately only after the password checked out, so a disabled
        # account is never revealed to someone who does not hold its password.
        raise AuthError("this account is disabled")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = datetime.now(UTC)
    session.commit()
    session.refresh(user)
    return user


def start_session(session: Session, user: User, lifetime_hours: int) -> IssuedSession:
    now = datetime.now(UTC)
    token = new_session_token()
    expires_at = now + timedelta(hours=lifetime_hours)
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            created_at=now,
            last_seen_at=now,
            expires_at=expires_at,
        )
    )
    session.commit()
    return IssuedSession(token=token, expires_at=expires_at)


def resolve_session(session: Session, token: str) -> User | None:
    """Return the signed-in user for a cookie value, or None if it is not usable."""
    if not token:
        return None
    record = session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    )
    if record is None or record.revoked_at is not None:
        return None
    now = datetime.now(UTC)
    if as_utc(record.expires_at) <= now:
        return None
    user = session.get(User, record.user_id)
    if user is None or not user.is_active:
        return None
    if now - as_utc(record.last_seen_at) > LAST_SEEN_REFRESH:
        record.last_seen_at = now
        session.commit()
    return user


def revoke_session(session: Session, token: str) -> None:
    if not token:
        return
    record = session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    )
    if record is None or record.revoked_at is not None:
        return
    record.revoked_at = datetime.now(UTC)
    session.commit()


def revoke_all_sessions(session: Session, user: User) -> int:
    now = datetime.now(UTC)
    records = list(
        session.scalars(
            select(UserSession).where(
                UserSession.user_id == user.id, UserSession.revoked_at.is_(None)
            )
        )
    )
    for record in records:
        record.revoked_at = now
    return len(records)


def purge_expired_sessions(session: Session) -> int:
    """Delete rows that can no longer authenticate anyone."""
    now = datetime.now(UTC)
    records = list(session.scalars(select(UserSession)))
    stale = [
        record
        for record in records
        if record.revoked_at is not None or as_utc(record.expires_at) <= now
    ]
    for record in stale:
        session.delete(record)
    session.commit()
    return len(stale)
