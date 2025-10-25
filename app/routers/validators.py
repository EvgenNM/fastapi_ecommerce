from fastapi import HTTPException, status
from sqlalchemy import select


async def validate_category(category, category_id, db):
    """
    Проверка существования категории
    """
    stmt = select(category).where(
            category.id == category_id,
            category.is_active == True
        )
    result = await db.scalars(stmt)
    category = result.first()
    if category is None:
        raise HTTPException(
            status_code=400, detail="Category not found"
        )
    return category


async def validate_one_review(model, user_id, db):
    """Валидация для модели ReviewModel по полю user_id"""
    model_objects = await db.scalars(select(model).where(
            model.user_id == user_id,
            model.is_active == True
        )
    )
    if model_objects.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Только один отзыв можно оставить на товар'
        )
