from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from app.models.cart_items import CartItem as CartItemModel
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from .validators import validate_category


async def commit_and_refresh(object_model, db: AsyncSession):
    await db.commit()
    await db.refresh(object_model)
    return object_model


async def create_object_model(model, values, db: AsyncSession):
    db_object = model(**values)
    db.add(db_object)
    db_object = await commit_and_refresh(db_object, db)
    return db_object


async def update_object_model(
    model, object_model, values, db: AsyncSession
):
    await db.execute(
        update(model)
        .where(model.id == object_model.id)
        .values(**values)
    )
    object_model = await commit_and_refresh(object_model, db)
    return object_model


async def get_active_object_model_or_404(
    model, model_id, db: AsyncSession, description="Product not found"
):
    stmt = select(model).where(
        model.id == model_id,
        model.is_active == True
    )
    product = await db.scalars(stmt)
    result = product.first()
    if result is None:
        raise HTTPException(
                status_code=404, detail=description
            )
    return result


async def get_active_object_model_or_404_and_validate_category(
    model, model_id, db: AsyncSession, model_category
):
    product = await get_active_object_model_or_404(model, model_id, db)
    await validate_category(
        category=model_category,
        category_id=product.category_id,
        db=db
    )
    return product


async def update_grade_product(product, db: AsyncSession):
    """Функция обновления рейтинга продукта"""
    product_raiting = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product.id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = product_raiting.scalar() or 0.0
    product.rating = avg_rating
    await db.commit()


def get_validators_filters(kwargs: dict):
    if (
        kwargs.get('min_price') is not None
        and kwargs.get('max_price') is not None
        and kwargs['min_price'] > kwargs['max_price']
    ):
        raise HTTPException(
            status_code=400,
            detail="min_price не может быть больше max_price",
        )
    filters = []
    if kwargs.get('category_id') is not None:
        filters.append(ProductModel.category_id == kwargs['category_id'])
    if kwargs.get('min_price') is not None:
        filters.append(ProductModel.price >= kwargs['min_price'])
    if kwargs.get('max_price') is not None:
        filters.append(ProductModel.price <= kwargs['max_price'])
    if kwargs.get('in_stock') is not None:
        filters.append(
            ProductModel.stock > 0
            if kwargs['in_stock']
            else
            ProductModel.stock == 0
        )
    if kwargs.get('seller_id', None) is not None:
        filters.append(ProductModel.seller_id == kwargs['seller_id'])
    if kwargs.get('is_active') is not None:
        filters.append(ProductModel.is_active == kwargs['is_active'])
    return filters


async def _ensure_product_available(db: AsyncSession, product_id: int) -> None:
    result = await db.scalars(
        select(ProductModel).where(
            ProductModel.id == product_id,
            ProductModel.is_active == True,
        )
    )
    product = result.first()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found or inactive",
        )


async def _get_cart_item(
    db: AsyncSession,
    user_id: int,
    product_id: int,
):
    result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == user_id,
            CartItemModel.product_id == product_id,
        )
    )
    return result.first()
