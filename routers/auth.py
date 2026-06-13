import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from schemas import UserCreate, UserLogin, UserOut, Token
from services.auth import hash_password, verify_password, create_access_token, decode_token

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Simple in-memory rate limiters
login_attempts = defaultdict(list)
register_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 5
MAX_REGISTER_ATTEMPTS = 3
LOGIN_WINDOW_MINUTES = 15
REGISTER_WINDOW_MINUTES = 60


def check_login_rate_limit(ip: str) -> bool:
    now = time.time()
    window_start = now - (LOGIN_WINDOW_MINUTES * 60)

    # Clean old attempts
    login_attempts[ip] = [t for t in login_attempts[ip] if t > window_start]

    if len(login_attempts[ip]) >= MAX_LOGIN_ATTEMPTS:
        return False

    login_attempts[ip].append(now)
    return True


def check_register_rate_limit(ip: str) -> bool:
    now = time.time()
    window_start = now - (REGISTER_WINDOW_MINUTES * 60)

    # Clean old attempts
    register_attempts[ip] = [t for t in register_attempts[ip] if t > window_start]

    if len(register_attempts[ip]) >= MAX_REGISTER_ATTEMPTS:
        return False

    register_attempts[ip].append(now)
    return True


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post("/register", response_model=Token)
async def register(
    request: Request,
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not check_register_rate_limit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many registration attempts. Please wait an hour.",
        )

    result = await db.execute(select(User).where(User.email == body.email.lower().strip()))
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = User(
        id=uuid.uuid4(),
        email=body.email.lower().strip(),
        hashed_password=hash_password(body.password),
        plan="free",
        docs_used_this_month=0,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    body: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    ip = request.client.host if request.client else "unknown"
    if not check_login_rate_limit(ip):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please wait 15 minutes.",
        )

    result = await db.execute(select(User).where(User.email == body.email.lower().strip()))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return current_user
