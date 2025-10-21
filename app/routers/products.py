from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_seller
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate
from app.db_depends import get_async_db
from .validators import validate_category
from .tools import (
    create_object_model,
    update_object_model,
    get_active_object_model_or_404_and_validate_category
)


# Создаём маршрутизатор для товаров
router = APIRouter(
    prefix="/products",
    tags=["products"],
)


@router.get(
        "/",
        response_model=list[ProductSchema],
        status_code=status.HTTP_200_OK
)
async def get_all_products(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех товаров.
    """
    stmt = select(ProductModel).where(ProductModel.is_active == True)
    products = await db.scalars(stmt)
    result = products.all()
    return result


@router.post(
        "/",
        response_model=ProductSchema,
        status_code=status.HTTP_201_CREATED
)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Создаёт новый товар.
    """
    await validate_category(
        CategoryModel,
        product.category_id,
        db)
    values = product.model_dump()
    values.update(seller_id=current_user.id)
    db_product = await create_object_model(
        model=ProductModel,
        values=values,
        db=db
    )
    return db_product


@router.get(
        "/category/{category_id}",
        response_model=list[ProductSchema],
        status_code=status.HTTP_200_OK
)
async def get_products_by_category(
    category_id: int, db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список товаров в указанной категории по её ID.
    """
    await validate_category(
        CategoryModel,
        category_id,
        db)
    stmt = select(ProductModel).where(
        ProductModel.is_active == True,
        ProductModel.category_id == category_id
    )
    products = await db.scalars(stmt)
    result = products.all()
    return result


@router.get(
        "/{product_id}",
        response_model=ProductSchema,
        status_code=status.HTTP_200_OK
)
async def get_product(
    product_id: int, db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает детальную информацию о товаре по его ID.
    """
    product = await get_active_object_model_or_404_and_validate_category(
        ProductModel, product_id, db, CategoryModel
    )
    return product


@router.put(
        "/{product_id}",
        response_model=ProductSchema,
        status_code=status.HTTP_200_OK
)
async def update_product(
    product_id: int,
    product_update: ProductCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Обновляет товар по его ID.
    """
    product = await get_active_object_model_or_404_and_validate_category(
        ProductModel, product_id, db, CategoryModel
    )
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own products"
        )
    product = await update_object_model(
        ProductModel, product, product_update.model_dump(), db
    )
    return product


@router.delete(
        "/{product_id}",
        status_code=status.HTTP_200_OK
)
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: UserModel = Depends(get_current_seller)
):
    """
    Удаляет товар по его ID.
    """
    product = await get_active_object_model_or_404_and_validate_category(
        ProductModel, product_id, db, CategoryModel
    )
    if product.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own products"
        )
    await update_object_model(
        ProductModel, product, {'is_active': False}, db
    )
    return {"status": "success", "message": "Product marked as inactive"}
