from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.db_depends import get_async_db
from app.models.users import User as UserModel
from app.models.profiles import Profile as ProfileModel
from app.schemas import ProfileCreate, ProfileSchemas
from app.service.tools import (
    create_object_model,
    update_object_model
)


router = APIRouter(
    prefix="/profiles",
    tags=["profiles"],
)


@router.post('/', response_model=ProfileSchemas)
async def create_profile(
    profile: ProfileCreate,
    db: AsyncSession = Depends(get_async_db),
    user: UserModel = Depends(get_current_user)
):
    profile_exam = await db.scalars(select(ProfileModel).where(
        ProfileModel.user_id == user.id
    )
    )
    if profile_exam.first() is not None:
        raise HTTPException(
            status_code=400,
            detail='Профиль можно создать только себе и единыжды'
        )
    new_profile = await create_object_model(
        model=ProfileModel,
        values=profile.model_dump() | {'user_id': user.id},
        db=db
    )
    return new_profile


@router.get('/', response_model=list[ProfileSchemas])
async def create_profile(
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.scalars(select(ProfileModel))
    return result.all()


@router.put('/', response_model=ProfileSchemas)
async def create_profile(
    profile_update: ProfileCreate,
    db: AsyncSession = Depends(get_async_db),
    user: UserModel = Depends(get_current_user)
):
    profile = await db.scalars(select(ProfileModel).where(
        ProfileModel.user_id == user.id
    )
    )
    profile = profile.first()
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail='Изменить можно только свой существующий профиль'
        )
    profile_after_update = await update_object_model(
        ProfileModel, profile, profile_update.model_dump(), db
    )
    return profile_after_update
