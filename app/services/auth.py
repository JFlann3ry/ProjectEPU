# ruff: noqa: I001
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from fastapi import Depends, HTTPException
from itsdangerous import URLSafeTimedSerializer
from passlib.context import CryptContext
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.core.settings import settings
from app.models.user import User, UserSession
from db import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = settings.SECRET_KEY
serializer = URLSafeTimedSerializer(SECRET_KEY)

# Password hashing


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


# User authentication


def authenticate_user(db: Session, email: str, password: str):
    user = (
        db.query(User)
        .filter(User.Email == email, User.IsActive, ~User.MarkedForDeletion)
        .first()
    )
    if user and verify_password(password, getattr(user, "HashedPassword", "")):
        return user
    return None


# In-memory rate limiter (per process). For multi-instance, replace with Redis.
_login_attempts = defaultdict(lambda: deque())


def is_login_rate_limited(key: str) -> bool:
    from time import time

    window = int(getattr(settings, "RATE_LIMIT_LOGIN_WINDOW_SECONDS", 900))
    limit = int(getattr(settings, "RATE_LIMIT_LOGIN_ATTEMPTS", 5))
    q = _login_attempts[key]
    now = time()
    # drop old
    while q and q[0] < now - window:
        q.popleft()
    return len(q) >= limit


def add_login_attempt(key: str):
    from time import time

    q = _login_attempts[key]
    q.append(time())


# Session management


def create_session(
    db: Session,
    user_id: int,
    expires_in_minutes: int = 60 * 24,
    ip_address: str = "",
    user_agent: str = "",
):
    session_id = uuid.uuid4()
    # Use aware UTC to avoid deprecation, but store naive UTC to match existing DB schema
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expires_at = now + timedelta(minutes=expires_in_minutes)
    session = UserSession(
        SessionID=session_id,
        UserID=user_id,
        CreatedAt=now,
        ExpiresAt=expires_at,
        IsActive=True,
        LastSeen=now,
        IPAddress=ip_address or None,
        UserAgent=user_agent or None,
    )
    db.add(session)
    db.commit()
    return session


def rotate_session(
    db: Session, old_session_id: str, user_id: int, ip_address: str = "", user_agent: str = ""
):
    """Deactivate the old session and create a new one."""
    deactivate_session(db, old_session_id)
    return create_session(db, user_id=user_id, ip_address=ip_address, user_agent=user_agent)


def get_session(db: Session, session_id: str):
    try:
        sid = uuid.UUID(str(session_id))
    except Exception:
        sid = session_id
    session = (
        db.query(UserSession)
        .filter(UserSession.SessionID == sid, UserSession.IsActive)
        .first()
    )
    if session is not None:
        expires_at = getattr(session, "ExpiresAt", None)
        if (
            isinstance(expires_at, datetime)
            and expires_at > datetime.now(timezone.utc).replace(tzinfo=None)
        ):
            setattr(
                session,
                "LastSeen",
                datetime.now(timezone.utc).replace(tzinfo=None),
            )
            db.commit()
            return session
    return None


def deactivate_session(db: Session, session_id: str):
    try:
        sid = uuid.UUID(str(session_id))
    except Exception:
        sid = session_id
    session = db.query(UserSession).filter(UserSession.SessionID == sid).first()
    if session:
        setattr(session, "IsActive", False)
        db.commit()


# User creation and email verification


def create_user(db: Session, first_name: str, last_name: str, email: str, password: str):
    hashed_pw = hash_password(password)
    user = User(
        FirstName=first_name,
        LastName=last_name,
        Email=email,
        HashedPassword=hashed_pw,
        EmailVerified=False,
        IsActive=True,
        MarkedForDeletion=False,
    )
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
        return user
    except IntegrityError:
        db.rollback()
        return None


def generate_email_token(email: str) -> str:
    token = serializer.dumps(email, salt="email-verify")
    return str(token)


def verify_email_token(token: str, max_age=3600 * 24) -> Optional[str]:
    try:
        email = serializer.loads(token, salt="email-verify", max_age=max_age)
        return str(email)
    except Exception:
        return None


# Helper to read user from request cookie


def get_user_id_from_request(request: Request, db: Session) -> Optional[int]:
    session_id = request.cookies.get("session_id")
    if not session_id:
        return None
    session_obj = get_session(db=db, session_id=session_id)
    if not session_obj:
        return None
    uid: Any = getattr(session_obj, "UserID", None)
    if isinstance(uid, int):
        return uid
    try:
        return int(str(uid)) if uid is not None else None
    except Exception:
        return None


# FastAPI dependencies for auth


def get_current_user(request: Request, db: Session = Depends(get_db)) -> Optional[User]:
    """Return the current authenticated User or None if not logged in/invalid.

    This uses the session cookie and validates activity/expiry.
    """
    uid = get_user_id_from_request(request, db)
    if uid is None:
        return None
    user = (
        db.query(User)
        .filter(
            User.UserID == uid,
            User.IsActive,
            ~User.MarkedForDeletion,
        )
        .first()
    )
    return user


def require_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Dependency that requires an authenticated user; redirects to /login if missing."""
    user = get_current_user(request, db)
    if not user:
        # Redirect to login
        raise HTTPException(status_code=302, headers={"Location": "/login"})
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    """Dependency that requires an admin user based on the IsAdmin flag."""
    if not bool(getattr(user, "IsAdmin", False)):
        raise HTTPException(status_code=403, detail="Forbidden")
    return user
