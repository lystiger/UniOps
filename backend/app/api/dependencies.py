"""Route guards.

Every data route names the access it needs. `read_access` accepts any signed-in
account, `write_access` narrows to the roles that may change data, and
`admin_access` to account administration. Nothing is protected by being absent
from a menu: the check is on the route.

The canonical product routes additionally accept the catalogue service key, so
another internal system (the Unigreen catalogue) can read products and request
new ones. The key is not a user: it opens only the routes that name
`catalog_read_access` or `catalog_create_access`, and nothing else.
"""

import hmac

from fastapi import Depends, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.errors import ApiError
from app.models import User, UserRole
from app.services import auth

WRITE_ROLES = (UserRole.ADMIN, UserRole.OFFICE)


async def current_user(request: Request, session: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name, "")
    user = auth.resolve_session(session, token)
    if user is None:
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="sign in to use UniOps",
            code="AUTH_REQUIRED",
        )
    return user


def _check_role(user: User, allowed: set[UserRole]) -> None:
    if user.role not in allowed:
        raise ApiError(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"the {user.role.value} role may not perform this action",
            code="PERMISSION_DENIED",
            params={"role": user.role.value},
        )


def require_roles(*roles: UserRole):
    allowed = set(roles)

    async def dependency(user: User = Depends(current_user)) -> User:
        _check_role(user, allowed)
        return user

    return dependency


CATALOG_SERVICE_KEY_HEADER = "x-uniops-catalog-key"


def _catalog_service_authenticated(request: Request) -> bool:
    """True when the request carries the configured catalogue service key.

    A request that presents a key which does not match is refused outright
    rather than falling back to the session, so a misconfigured integration
    fails with a clear reason instead of a generic sign-in error.
    """
    presented = request.headers.get(CATALOG_SERVICE_KEY_HEADER)
    if presented is None:
        return False
    configured = get_settings().catalog_service_key
    if configured is None or not hmac.compare_digest(
        presented.encode(), configured.get_secret_value().encode()
    ):
        raise ApiError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="the catalogue service key was not accepted",
            code="CATALOG_SERVICE_KEY_INVALID",
        )
    return True


def _catalog_access(*roles: UserRole):
    allowed = set(roles)

    async def dependency(request: Request, session: Session = Depends(get_db)) -> None:
        if _catalog_service_authenticated(request):
            return
        _check_role(await current_user(request, session), allowed)

    return dependency


read_access = Depends(current_user)
write_access = Depends(require_roles(*WRITE_ROLES))
admin_access = Depends(require_roles(UserRole.ADMIN))
catalog_read_access = Depends(_catalog_access(*UserRole))
catalog_create_access = Depends(_catalog_access(*WRITE_ROLES))
