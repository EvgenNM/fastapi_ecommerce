import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi.security import OAuth2PasswordRequestForm

import app.constants as c
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    get_current_user
)
from app.config import SECRET_KEY, ALGORITHM, NAME_TOKEN_HEAD
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.schemas import UserCreate, User as UserSchema, UserRead
from app.service.tools import create_object_model


router = APIRouter(prefix='/users', tags=["users"])


@router.post(
        "/", response_model=UserSchema, status_code=status.HTTP_201_CREATED
)
async def create_user(
    user: UserCreate, db: AsyncSession = Depends(get_async_db)
):
    """Регистрирует нового пользователя"""

    # Проверка уникальности email
    result = await db.scalars(
        select(UserModel).where(UserModel.email == user.email)
    )
    if result.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    db_user = await create_object_model(
        UserModel,
        {
            'email': user.email,
            'hashed_password': hash_password(user.password),
            'role': user.role
        },
        db
    )
    return db_user


@router.get('/', response_model=list[UserRead])
async def get_users(
    db: AsyncSession = Depends(get_async_db)
):
    users = await db.scalars(select(UserModel).options(
        selectinload(UserModel.profile)
        )
    )
    return users.all()


@router.get('/me', response_model=UserRead)
async def get_users(
    db: AsyncSession = Depends(get_async_db),
    user: UserModel = Depends(get_current_user)
):
    users = await db.scalars(
        select(UserModel)
        .where(UserModel.id == user.id)
        .options(selectinload(UserModel.profile)
    )
    )
    return users.first()


@router.post('/token')
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
) -> dict:
    result = await db.scalars(
        select(UserModel).where(
            UserModel.email == form_data.username,
            UserModel.is_active == True
        )
    )
    user = result.first()
    if not user or not verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": NAME_TOKEN_HEAD},
        )
    access_token = create_access_token(
        data={
            c.TOKEN_DICT_KEY_EMAIL: user.email,
            c.TOKEN_DICT_KEY_ROLE: user.role,
            c.TOKEN_DICT_KEY_ID: user.id
        }
    )
    refresh_token = create_refresh_token(
        data={
            c.TOKEN_DICT_KEY_EMAIL: user.email,
            c.TOKEN_DICT_KEY_ROLE: user.role,
            c.TOKEN_DICT_KEY_ID: user.id
        }
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": NAME_TOKEN_HEAD
    }


@router.post("/refresh-token")
async def refresh_token(
    refresh_token: str, db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет access_token с помощью refresh_token.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": NAME_TOKEN_HEAD},
    )
    try:
        payload = jwt.decode(
            refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get(c.TOKEN_DICT_KEY_EMAIL)
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    result = await db.scalars(select(UserModel).where(
        UserModel.email == email, UserModel.is_active == True)
    )
    user = result.first()
    if user is None:
        raise credentials_exception
    access_token = create_access_token(
        data={
            c.TOKEN_DICT_KEY_EMAIL: user.email,
            c.TOKEN_DICT_KEY_ROLE: user.role,
            c.TOKEN_DICT_KEY_ID: user.id}
    )
    return {"access_token": access_token, "token_type": NAME_TOKEN_HEAD}
