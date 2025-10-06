from fastapi import HTTPException
from sqlalchemy import select


def validate_category(category, category_id, db):
    """
    Проверка существования категории
    """
    if category_id is not None:
        stmt = select(category).where(
                category.id == category_id,
                category.is_active == True
            )
        category = db.scalars(stmt).first()
        if category is None:
            raise HTTPException(
                status_code=400, detail="Category not found"
            )
    return category
