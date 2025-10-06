from fastapi import HTTPException
from sqlalchemy import select, update

from .validators import validate_category


def create_object_model(model, values, db):
    db_object = model(**values)
    db.add(db_object)
    db.commit()
    db.refresh(db_object)
    return db_object


def update_object_model(model, object, values, db):
    db.execute(
        update(model)
        .where(model.id == object.id)
        .values(**values)
    )
    db.commit()
    db.refresh(object)
    return object


def get_object_model(stmt, db):
    product = db.scalars(stmt).first()
    if product is None:
        raise HTTPException(
                status_code=404, detail="Product not found"
            )
    return product


def get_active_object_model_or_404(model, model_id, db):
    stmt = select(model).where(
        model.id == model_id,
        model.is_active == True
    )
    product = db.scalars(stmt).first()
    if product is None:
        raise HTTPException(
                status_code=404, detail="Product not found"
            )
    return product


def get_active_object_model_or_404_and_validate_category(
    model, model_id, db, model_category
):
    product = get_active_object_model_or_404(model, model_id, db)
    validate_category(
        category=model_category,
        category_id=product.category_id,
        db=db
    )
    return product
