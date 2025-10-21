import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi.security import OAuth2PasswordRequestForm

from app.config import SECRET_KEY, ALGORITHM
from app.models.users import User as UserModel
from app.schemas import UserCreate, User as UserSchema
from app.db_depends import get_async_db
from app.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token
)

from .tools import create_object_model

router = APIRouter(prefix="/users", tags=["users"])


@router.post(
        "/", response_model=UserSchema, status_code=status.HTTP_201_CREATED
)
async def create_user(
    user: UserCreate, db: AsyncSession = Depends(get_async_db)
):
    """
    Регистрирует нового пользователя с ролью 'buyer' или 'seller'.
    """

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


@router.get('/')
async def get_users(
    db: AsyncSession = Depends(get_async_db)
) -> list[UserSchema]:
    users = await db.scalars(select(UserModel))
    return users.all()


@router.post('/token')
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
):
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
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.email, "role": user.role, "id": user.id}
    )
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
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
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
        )
        email: str = payload.get("sub")
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
        data={"sub": user.email, "role": user.role, "id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}
