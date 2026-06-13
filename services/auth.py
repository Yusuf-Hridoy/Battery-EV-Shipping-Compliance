import os
from datetime import datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


PLAN_LIMITS = {
    "free": 3,
    "starter": 20,
    "growth": 999999,
}


def check_plan_limit(plan: str, docs_used: int, perdoc_credits: int = 0) -> dict:
    limit = PLAN_LIMITS.get(plan, 3)

    if docs_used < limit:
        return {"allowed": True, "reason": "ok", "use_credit": False}

    if perdoc_credits > 0:
        return {"allowed": True, "reason": "use_credit", "use_credit": True}

    return {
        "allowed": False,
        "reason": "limit_reached",
        "use_credit": False,
    }
