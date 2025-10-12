from fastapi import HTTPException
from sqlalchemy import select, update

from .validators import validate_category


async def create_object_model(model, values, db):
    db_object = model(**values)
    db.add(db_object)
    await db.commit()
    await db.refresh(db_object)
    return db_object


async def update_object_model(model, object_model, values, db):
    await db.execute(
        update(model)
        .where(model.id == object_model.id)
        .values(**values)
    )
    await db.commit()
    await db.refresh(object_model)
    return object_model


async def get_active_object_model_or_404(model, model_id, db):
    stmt = select(model).where(
        model.id == model_id,
        model.is_active == True
    )
    product = await db.scalars(stmt)
    result = product.first()
    if not product:
        raise HTTPException(
                status_code=404, detail="Product not found"
            )
    return result


async def get_active_object_model_or_404_and_validate_category(
    model, model_id, db, model_category
):
    try:
        product = await get_active_object_model_or_404(model, model_id, db)
        await validate_category(
            category=model_category,
            category_id=product.category_id,
            db=db
        )
    except:
        pass
    return product
