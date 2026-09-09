"""Password hashing and session-token primitives.

Passwords use Argon2id through `argon2-cffi` with the library's current default
parameters. Session cookie values are random 256-bit tokens; only their SHA-256
digest is persisted, so the stored row cannot be replayed as a live session.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()

# A hash of a value nobody can present, verified against whenever the supplied
# username does not exist. Without it a missing user answers far faster than a
# wrong password and the response time alone enumerates valid usernames.
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))

MIN_PASSWORD_LENGTH = 12


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


def spend_dummy_verification() -> None:
    """Burn one Argon2 verification so an unknown username costs the same."""
    verify_password(_DUMMY_HASH, secrets.token_urlsafe(32))


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def as_utc(value: datetime) -> datetime:
    """Read a stored timestamp as UTC.

    SQLite has no timezone type and hands back a naive datetime for the same
    column Postgres returns aware. Comparing the naive value against an aware
    `now` raises, so every stored timestamp is normalised on the way out.
    """
    return value if value.tzinfo else value.replace(tzinfo=UTC)
