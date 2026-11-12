from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import read_session_token
from app.db.session import get_db
from app.models import User


def current_user(request: Request, db: Session = Depends(get_db), token: str | None = Cookie(default=None, alias=settings.session_cookie)) -> User:
    authorization = request.headers.get("authorization", "")
    if authorization.lower().startswith("bearer "):
        token = authorization[7:].strip()
    user_id = read_session_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Session is no longer valid")
    return user
