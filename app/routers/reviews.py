from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from app.auth import get_current_buyer
from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.db_depends import get_async_db
from .validators import validate_category
from .tools import (
    create_object_model,
    update_object_model,
    get_active_object_model_or_404,
    get_active_object_model_or_404_and_validate_category
)


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.get('/')
async def get_reviews(
    db: AsyncSession = Depends(get_async_db)
) -> list[ReviewSchema]:
    reviews_db = await db.scalars(select(ReviewModel))
    return reviews_db.all()


@router.post('/')
async def create_review(
    review: ReviewCreate,
    db: AsyncSession = Depends(get_async_db),
    current_buyer: UserModel = Depends(get_current_buyer)
) -> ReviewSchema:
    
    # Валидация на наличие активного продукта
    product = await get_active_object_model_or_404(
        ProductModel, review.product_id, db
    )

    # Валидация единственности отзыва на товар данного юзера
    validate_first_review = await db.scalars(select(ReviewModel).where(
        ReviewModel.user_id == current_buyer.id,
        ReviewModel.is_active == True
    )
    )
    if validate_first_review.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Только один отзыв можно оставить на товар'
        )
    
    # Создание нового отзыва
    values = review.model_dump()
    values.update(user_id=current_buyer.id)
    new_review = await create_object_model(
        model=ReviewModel,
        values=values,
        db=db
    )

    # Обновление рейтинга товара
    product_raiting = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product.id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = product_raiting.scalar() or 0.0
    product.rating = avg_rating
    await db.commit()

    return new_review