import asyncio
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from fastapi_filter import FilterDepends
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

import app.constants as c
from app.auth import get_current_buyer
from app.database import async_session_maker
from app.db_depends import get_async_db
from app.filters import ProductFilter
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.cart_items import CartItem as CartItemModel
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

router_read = APIRouter(prefix='/orders', tags=["orders"])


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


async def create_one_order(product_id, quantity, buyer, db):
    """ Функция по созданию одного заказа"""

    # Валидация и получение продукта по id
    product = await get_active_object_model_or_404(
        ProductModel, product_id, db
    )

    # Проверка наличия соответ. количеста продукта
    if product.stock < quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not enough stock for product {product.name}",
        )
    price = Decimal(product.price)

    # Валидация цены продукта
    if price is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Product {product.name} has no price set",
        )
    total = quantity * price

    # Создание нового заказа
    order = await create_object_model(
        Order, {'total': total, 'buyer_id': buyer.id}, db
    )

    # Создание записи деталей заказа в промежуточной таблице OrderItem
    # таблиц Order и Product
    new_order_item = await create_object_model(
        OrderItem,
        {
            'order_id': order.id,
            'product_id': product.id,
            'quantity': quantity,
            'price': price
        },
        db
    )

    # Обновляем значение количества единиц продукта
    product.stock -= quantity
    await db.commit()

    # Получение полной инф-и о заказе, его деталях и продукте заказа
    order_item = await db.scalars(select(OrderItem)
        .where(
            OrderItem.order_id == new_order_item.order_id,
            OrderItem.product_id == new_order_item.product_id
        )
        .options(selectinload(OrderItem.product))
        .options(selectinload(OrderItem.order))
        )
    return order_item.first()


async def create_order_with_cart_item(cart_item, buyer):
    """
    Функция по созданию одного заказа с исключением
    конфликта сессий для асинхронного процесса загрузки моделей пачкой
    """

    quantity = cart_item.quantity
    product_id = cart_item.product.id
    async with async_session_maker() as db:
        order_item = await create_one_order(product_id, quantity, buyer, db)
    return order_item

@router_read.post('/checkout', response_model=list[OrderItemSchemas])
async def checkout_order(
    buyer: UserModel = Depends(get_current_buyer),
    db: AsyncSession = Depends(get_async_db)
):

    items = await db.scalars(
        select(CartItemModel)
        .where(CartItemModel.user_id == buyer.id)
        .options(selectinload(CartItemModel.product))
        .order_by(CartItemModel.id)
    )
    cart_items = items.all()
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Корзина пуста"
        )

    tasks = [
        asyncio.create_task(
            create_order_with_cart_item(cart_item, buyer),
            name=str(cart_item.id)
        ) for cart_item in cart_items
    ]
    total_orders = len(tasks)
    done_add_order, pending_order = await asyncio.wait(tasks)

    order_item_id_done = []
    for order_item in done_add_order:
        if order_item.exception() is None:
            order_item_id_done.append(int(order_item.get_name()))
    done_count_orders = len(order_item_id_done)

    for task in pending_order:
        task.cancel()

    if order_item_id_done:
        await db.execute(delete(CartItemModel).where(
            CartItemModel.user_id == buyer.id,
            CartItemModel.id.in_(order_item_id_done)
        )
        )
        await db.commit()

    if total_orders != done_count_orders:
        fail_order_items_products = [
            cart_item.product.name for cart_item in cart_items
            if cart_item.id not in order_item_id_done
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Произошла ошибка при оформлении заказа(-ов) и "
                f"не оформлен(-о) {total_orders - done_count_orders} заказ(-а):"
                f" {', '.join(fail_order_items_products)}"
            )
        )
    return [add_order.result() for add_order in done_add_order]
