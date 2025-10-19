from fastapi import HTTPException
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
