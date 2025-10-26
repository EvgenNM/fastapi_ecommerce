from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.sql import func

from app.models.reviews import Review as ReviewModel
from .validators import validate_category


async def commit_and_refresh(object_model, db):
    await db.commit()
    await db.refresh(object_model)
    return object_model


async def create_object_model(model, values, db):
    db_object = model(**values)
    db.add(db_object)
    # await db.commit()
    # await db.refresh(db_object)
    db_object = await commit_and_refresh(db_object, db)
    return db_object


async def update_object_model(model, object_model, values, db):
    await db.execute(
        update(model)
        .where(model.id == object_model.id)
        .values(**values)
    )
    # await db.commit()
    # await db.refresh(object_model)
    object_model = await commit_and_refresh(object_model, db)
    return object_model


async def get_active_object_model_or_404(
    model, model_id, db, description="Product not found"
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
    model, model_id, db, model_category
):
    product = await get_active_object_model_or_404(model, model_id, db)
    await validate_category(
        category=model_category,
        category_id=product.category_id,
        db=db
    )
    return product


async def update_grade_product(product, db):
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
