from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import app.constants as c
from app.config import (
    SECRET_KEY,
    ALGORITHM,
    TOKEN_URL,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    NAME_TOKEN_HEAD
)
from app.db_depends import get_async_db
from app.models.users import User as UserModel

# контекст для хеширования с использованием bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=TOKEN_URL)


def hash_password(password: str) -> str:
    """Преобразует пароль в хеш с использованием bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли введённый пароль сохранённому хешу.
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
    """Создаёт JWT"""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=ACCESS_TOKEN_EXPIRE_MINUTES
    )
    to_encode.update({c.TOKEN_DICT_KEY_EXPIRE: expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict):
    """Создаёт рефреш-токен с длительным сроком действия"""

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=REFRESH_TOKEN_EXPIRE_DAYS
    )
    to_encode.update({c.TOKEN_DICT_KEY_EXPIRE: expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_async_db)
):
    """Проверяет JWT и возвращает пользователя из базы"""

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail='Could not validate credentials',
        headers={'WWW-Authenticate': NAME_TOKEN_HEAD},
    )
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get(c.TOKEN_DICT_KEY_EMAIL)
        if email is None:
            raise credentials_exception
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Token has expired',
            headers={'WWW-Authenticate': NAME_TOKEN_HEAD},
        )
    except jwt.PyJWTError:
        raise credentials_exception
    result = await db.scalars(
        select(UserModel).where(
            UserModel.email == email,
            UserModel.is_active == True
        )
    )
    user = result.first()
    if user is None:
        raise credentials_exception
    return user


async def get_current_seller(
        current_user: UserModel = Depends(get_current_user)
):
    """
    Проверяет, что пользователь имеет роль 'seller'.
    """
    if current_user.role != c.USER_NAME_ROLE_SELLER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f'Only {c.USER_NAME_ROLE_SELLER} can perform this action'
            )
        )
    return current_user


async def get_current_buyer(
    current_user: UserModel = Depends(get_current_user)
):
    if current_user.role != c.USER_NAME_ROLE_BUYER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'Only for {c.USER_NAME_ROLE_BUYER}'
        )
    return current_user


async def get_current_admin(
    current_user: UserModel = Depends(get_current_user)
):
    if current_user.role != c.USER_NAME_ROLE_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f'Only for {c.USER_NAME_ROLE_ADMIN}'
        )
    return current_user
