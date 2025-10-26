from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_buyer, get_current_admin
from app.models.reviews import Review as ReviewModel
from app.models.products import Product as ProductModel
from app.models.users import User as UserModel
from app.schemas import Review as ReviewSchema, ReviewCreate
from app.db_depends import get_async_db
from .validators import validate_one_review
from .tools import (
    create_object_model,
    update_object_model,
    get_active_object_model_or_404,
    update_grade_product
)


router = APIRouter(
    prefix="/reviews",
    tags=["reviews"],
)


@router.get('/', response_model=list[ReviewSchema])
async def get_reviews(
    db: AsyncSession = Depends(get_async_db)
):
    reviews_db = await db.scalars(select(ReviewModel).where(
        ReviewModel.is_active == True
    )
    )
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
    await validate_one_review(ReviewModel, current_buyer.id, db)

    # Создание нового отзыва
    new_review = await create_object_model(
        model=ReviewModel,
        values=review.model_dump() | {'user_id': current_buyer.id},
        db=db
    )

    # Обновление рейтинга товара
    await update_grade_product(product, db)

    return new_review


@router.get(
    '/products/{product_id}/reviews/',
    response_model=list[ReviewSchema]
)
async def get_product_reviews(
    product_id: int, db: AsyncSession = Depends(get_async_db)
):

    product = await get_active_object_model_or_404(
        ProductModel, product_id, db
    )
    reviews_db = await db.scalars(
        select(ReviewModel).where(
            ReviewModel.product_id == product.id,
            ReviewModel.is_active == True
        )
    )
    return reviews_db.all()


@router.delete('/reviews/{review_id}')
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_async_db),
    admin: UserModel = Depends(get_current_admin)
) -> dict:

    # Проверка наличия активного отзыва
    review = await get_active_object_model_or_404(
        ReviewModel, review_id, db, description='Review not found'
    )

    product = await get_active_object_model_or_404(
        ProductModel, review.product_id, db
    )
    # Мягкое удаление отзыва
    await update_object_model(ReviewModel, review, {'is_active': False}, db)

    await update_grade_product(product, db)

    return {"message": "Review deleted"}
