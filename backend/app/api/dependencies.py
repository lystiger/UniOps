"""Route guards.

Every data route names the access it needs. `read_access` accepts any signed-in
account, `write_access` narrows to the roles that may change data, and
`admin_access` to account administration. Nothing is protected by being absent
from a menu: the check is on the route.
"""

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import User, UserRole
from app.services import auth

WRITE_ROLES = (UserRole.ADMIN, UserRole.OFFICE)


async def current_user(request: Request, session: Session = Depends(get_db)) -> User:
    settings = get_settings()
    token = request.cookies.get(settings.session_cookie_name, "")
    user = auth.resolve_session(session, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="sign in to use UniOps"
        )
    return user


def require_roles(*roles: UserRole):
    allowed = set(roles)

    async def dependency(user: User = Depends(current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"the {user.role.value} role may not perform this action",
            )
        return user

    return dependency


read_access = Depends(current_user)
write_access = Depends(require_roles(*WRITE_ROLES))
admin_access = Depends(require_roles(UserRole.ADMIN))
