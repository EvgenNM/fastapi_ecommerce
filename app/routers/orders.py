import asyncio

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

import app.constants as c
from app.auth import get_current_buyer
from app.db_depends import get_async_db
from app.models.cart_items import CartItem as CartItemModel
from app.models.orders import Order, OrderItem
from app.models.users import User as UserModel
from app.schemas import OrderItem as OrderItemSchemas
from app.service.tools import (
    create_one_order,
    get_list_order_item_id_done,
    create_order_with_cart_item
)


router = APIRouter(
    prefix="/{product_id}/orders",
    tags=["orders"],
)

router_1 = APIRouter(prefix='/orders', tags=["orders"])


@router.post('/', response_model=OrderItemSchemas)
async def create_order(
    product_id: int,
    buyer: UserModel = Depends(get_current_buyer),
    quantity: int = Query(ge=1, le=100, default=1),
    db: AsyncSession = Depends(get_async_db)
):
    """Создание единичного заказа"""
    order_item = await create_one_order(product_id, quantity, buyer, db)
    return order_item


@router_1.get('/', response_model=list[OrderItemSchemas])
async def list_order_items(
    db: AsyncSession = Depends(get_async_db),
    buyer: UserModel = Depends(get_current_buyer)
):
    """
    Получение (чтение) всех созданных заказов в
    приложении конкретного покупателя
    """
    result = await db.scalars(
        select(OrderItem)
        .options(selectinload(OrderItem.product))
        .options(selectinload(OrderItem.order))
        )
    order_items = [
        order_item for order_item in result.all()
        if order_item.order.buyer_id == buyer.id
    ]
    return order_items


@router_1.post('/checkout', response_model=list[OrderItemSchemas])
async def checkout_order(
    buyer: UserModel = Depends(get_current_buyer),
    db: AsyncSession = Depends(get_async_db)
):
    """
    Оформление всех заказов пользователя, которые тот сформировал
    у себя в корзине с последующим выводом деталей заказов,
    содержащих сведения как о самом заказе, так и о продукте заказа
    """

    # Получение всех добавленных в корзину продуктов
    # конкретного покупателя
    items = await db.scalars(
        select(CartItemModel)
        .where(CartItemModel.user_id == buyer.id)
        .options(selectinload(CartItemModel.product))
        .order_by(CartItemModel.id)
    )
    cart_items = items.all()

    # Валидация корзины покупателя на пустоту
    if not cart_items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Корзина пуста"
        )

    # Создание задач по оформлению "финишных" заказов для asyncio.wait
    # с присвоением каждой задаче в качестве имени - id модели деталей
    # оформленного в корзине товара (CartItem)
    tasks = [
        asyncio.create_task(
            create_order_with_cart_item(cart_item, buyer),
            name=str(cart_item.id)
        ) for cart_item in cart_items
    ]
    total_orders = len(tasks)

    # Запуск задач по оформлению "финишных" заказов
    done_orders, pending_order = await asyncio.wait(tasks)

    # получение списка id моделей деталей заказов (CartItem)
    # сформированных в корзине и успешно оформленных как "финишные" заказы
    order_item_id_done = get_list_order_item_id_done(done_orders)
    done_count_orders = len(order_item_id_done)

    # Страховочная (перспективная) процедура отмены ожидающих выполнения задач
    # по оформлению "финишных" заказов, в случае остановки процесса оформ-ия
    for task in pending_order:
        task.cancel()

    # Чистка корзины от успешно оформленных заказов - удаление всех
    # соответствующих моделей заказов корзины (CartItem) у пользователя,
    # оформившего заказ
    if order_item_id_done:
        await db.execute(delete(CartItemModel).where(
            CartItemModel.user_id == buyer.id,
            CartItemModel.id.in_(order_item_id_done)
        )
        )
        await db.commit()

    # Проверка, что все ли заказы из корзины прошли успешное "финишное"
    # оформление и вывод в противном случае соотв. сообщения и
    # названиями продуктов, заказы на которые не прошли оформление
    if total_orders != done_count_orders:
        fail_order_items_products = [
            cart_item.product.name for cart_item in cart_items
            if cart_item.id not in order_item_id_done
        ]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Произошла ошибка при оформлении заказа(-ов) и не "
                f"оформлен(-о) {total_orders - done_count_orders} заказ(-а):"
                f" {', '.join(fail_order_items_products)}"
            )
        )
    # Вывод списка моделей деталей заказов в случае успешного "финишного"
    # оформления всех сформированных в корзине заказов
    return [add_order.result() for add_order in done_orders]
