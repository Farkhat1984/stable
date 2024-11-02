import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import get_db
from app.models.models import User
from ..schemas.schemas import UserResponse, UserCreate, TokenData, Token
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm



DB_USER: str = os.environ["DB_USER"]
DB_PASSWORD: str = os.environ["DB_PASSWORD"]
DB_HOST: str = os.environ["DB_HOST"]
DB_NAME: str = os.environ["DB_NAME"]
DB_PORT: int = int(os.environ["DB_PORT"])  # Convert to int

# JWT settings
SECRET_KEY: str = os.environ["SECRET_KEY"]
ALGORITHM: str = os.environ["ALGORITHM"]
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"])  # Convert to int
# --- Pydantic models ---


# --- Constants and utilities ---
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/token")
auth_router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash"""
    return pwd_context.hash(password)


def create_access_token(user: User, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT token with user data"""
    to_encode = {
        "user_id": user.id,
        "is_superuser": user.is_superuser,
        "sub": user.login  # сохраняем для совместимости
    }

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def authenticate_user(session: AsyncSession, login: str, password: str) -> Optional[User]:
    """Authenticate user by login and password"""
    query = select(User).where(User.login == login)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_db)
) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("user_id")
        is_superuser: bool = payload.get("is_superuser", False)

        if user_id is None:
            raise credentials_exception

        token_data = TokenData(user_id=user_id, is_superuser=is_superuser)
    except JWTError:
        raise credentials_exception

    query = select(User).where(User.id == token_data.user_id)
    result = await session.execute(query)
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    return user


async def get_current_active_admin(
        current_user: User = Depends(get_current_user)
) -> User:
    """Check if current user is admin"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges"
        )
    return current_user







@auth_router.post("/token", response_model=Token)
async def login_for_access_token(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_db)
):
    """Login endpoint to get JWT token"""
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user=user,  # Передаем весь объект пользователя
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}


# Обновляем register_user
@auth_router.post("/register", response_model=Token)
async def register_user(
        user_data: UserCreate,
        session: AsyncSession = Depends(get_db)
):
    """Register new user"""
    # Проверка существующего пользователя остается такой же...

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        login=user_data.login,
        email=user_data.email,
        password=hashed_password,
        phone=user_data.phone
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    # Create and return token с обновленной функцией
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        user=new_user,  # Передаем весь объект пользователя
        expires_delta=access_token_expires
    )

    return {"access_token": access_token, "token_type": "bearer"}

# Optional: Password change endpoint
@auth_router.post("/change-password")
async def change_password(
        old_password: str,
        new_password: str,
        current_user: User = Depends(get_current_user),
        session: AsyncSession = Depends(get_db)
):
    """Change user password"""
    if not verify_password(old_password, current_user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password"
        )

    current_user.password = get_password_hash(new_password)
    await session.commit()

    return {"message": "Password updated successfully"}


# Optional: User profile endpoint
@auth_router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user