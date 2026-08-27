from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth import get_user_from_token

SESSION_COOKIE_NAME = "session_token"


class NotAuthenticated(Exception):
    """Raised when a request has no valid session. Handled centrally in
    app/main.py: a JSON 401 for /api/* routes, a redirect to /login for
    HTML page routes -- so every route (API or page) can depend on
    `get_current_user` the same way regardless of which response it needs.
    """


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    user = get_user_from_token(db, token) if token else None
    if user is None:
        raise NotAuthenticated()
    return user
