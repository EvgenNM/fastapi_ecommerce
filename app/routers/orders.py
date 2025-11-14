from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi_filter import FilterDepends
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

import app.constants as c
from app.auth import get_current_buyer
from app.db_depends import get_async_db
from app.filters import ProductFilter
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.orders import Order, OrderItem
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, OrderItem as OrderItemSchemas
from app.service.validators import validate_category
from app.service.tools import (
    create_object_model,
    update_object_model,
    get_active_object_model_or_404,
    commit_and_refresh
)


router = APIRouter(
    prefix="/{product_id}/orders",
    tags=["orders"],
)

router_read = APIRouter(prefix='/orders_read', tags=["orders"])


@router.post('/', response_model=OrderItemSchemas)
async def create_order(
    product_id: int,
    buyer: UserModel = Depends(get_current_buyer),
    quantity: int = Query(ge=1, le=100, default=1),
    db: AsyncSession = Depends(get_async_db)
):
    product = await get_active_object_model_or_404(
        ProductModel, product_id, db, description="Product not found"
    )
    total = quantity * product.price
    order = await create_object_model(
        Order, {'total': total, 'buyer_id': buyer.id}, db
    )
    new_order_item = await create_object_model(
        OrderItem,
        {
            'order_id': order.id,
            'product_id': product.id,
            'quantity': quantity,
            'price': product.price
        },
        db
    )
    order_item = await db.scalars(select(OrderItem)
        .where(
            OrderItem.order_id == new_order_item.order_id,
            OrderItem.product_id == new_order_item.product_id
        )
        .options(selectinload(OrderItem.product))
        .options(selectinload(OrderItem.order))
        )
    return order_item.first()


@router_read.get('/', response_model=list[OrderItemSchemas])
async def list_order_items(
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.scalars(select(OrderItem)
        .options(selectinload(OrderItem.product))
        .options(selectinload(OrderItem.order))
        )
    order_items = result.all()
    return order_items
