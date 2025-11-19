from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi_filter import FilterDepends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.constants as c
from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.filters import ProductFilter
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.service.validators import validate_category
from app.service.tools import (
    create_object_model,
    update_object_model,
    get_active_object_model_or_404_and_validate_category,
    get_validators_filters
)


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


router_filter_model = APIRouter(
    prefix="/products_filter_model",
    tags=["products"],
)


@router_filter_model.get(
    '/',
    response_model=list[ProductSchema]
)
async def get_filter_products(
    product_filter: ProductFilter = FilterDepends(ProductFilter),
    page: int = Query(
        ge=c.PRODUCT_ROUTER_MIN_PAGE, default=c.PRODUCT_ROUTER_MIN_PAGE),
    size: int = Query(
        ge=c.PRODUCT_ROUTER_MIN_SIZE,
        le=c.PRODUCT_ROUTER_MAX_SIZE,
        default=c.PRODUCT_ROUTER_DEFAULT_SIZE
    ),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Возвращает список товаров с возможностью фильтрации.
    """
    filter_objects = await db.scalars(product_filter.filter(
        select(ProductModel)
        .where(ProductModel.is_active == True)
        .order_by(ProductModel.id)
        .offset((page - 1) * size)
        .limit(size)
    )
    )
    return filter_objects.all()


@router.get(
    '/',
    response_model=ProductList
)
async def get_all_products(
        page: int = Query(
            default=c.PRODUCT_ROUTER_MIN_PAGE,
            ge=c.PRODUCT_ROUTER_MIN_PAGE
        ),
        page_size: int = Query(
            ge=c.PRODUCT_ROUTER_MIN_SIZE,
            le=c.PRODUCT_ROUTER_MAX_SIZE,
            default=c.PRODUCT_ROUTER_DEFAULT_SIZE
        ),
        category_id: int | None = Query(
            None, description="ID категории для фильтрации"),
        min_price: float | None = Query(
            None,
            ge=c.PRODUCT_MIN_PRICE,
            description="Минимальная цена товара"),
        max_price: float | None = Query(
            None,
            ge=c.PRODUCT_MAX_PRICE,
            description="Максимальная цена товара"),
        in_stock: bool | None = Query(
            None,
            description=(
                "true — только товары в наличии, false — только без остатка"
            )
            ),
        seller_id: int | None = Query(
            None, description="ID продавца для фильтрации"),
        db: AsyncSession = Depends(get_async_db),
):
    """
    Возвращает список всех активных товаров.
    """
    filter_args = {
        'category_id': category_id,
        'min_price': min_price,
        'max_price': max_price,
        'in_stock': in_stock,
        'seller_id': seller_id,
        'is_active': True
    }
    validators_filters = get_validators_filters(filter_args)

    total_stmt = select(func.count()).select_from(
        ProductModel
    ).where(ProductModel.is_active == True)
    total = await db.scalar(total_stmt) or 0

    products_stmt = (
        select(ProductModel)
        .where(*validators_filters)
        .order_by(ProductModel.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = (await db.scalars(products_stmt)).all()
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


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
    db_product = await create_object_model(
        model=ProductModel,
        values=product.model_dump() | {'seller_id': current_user.id},
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
