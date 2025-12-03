import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status, UploadFile, File, Form
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

import app.config as conf
from app.database import async_session_maker
from app.models.cart_items import CartItem as CartItemModel
from app.models.orders import Order, OrderItem
from app.models.products import Product as ProductModel
from app.models.reviews import Review as ReviewModel
from .validators import validate_category


async def commit_and_refresh(object_model, db: AsyncSession):
    await db.commit()
    await db.refresh(object_model)
    return object_model


async def create_object_model(model, values, db: AsyncSession):
    db_object = model(**values)
    db.add(db_object)
    db_object = await commit_and_refresh(db_object, db)
    return db_object


async def update_object_model(
    model, object_model, values, db: AsyncSession
):
    await db.execute(
        update(model)
        .where(model.id == object_model.id)
        .values(**values)
    )
    object_model = await commit_and_refresh(object_model, db)
    return object_model


async def get_active_object_model_or_404(
    model, model_id, db: AsyncSession, description="Product not found"
):
    stmt = select(model).where(
        model.id == model_id,
        model.is_active == True
    )
    product = await db.scalars(stmt)
    result = product.first()
    if result is None:
        raise HTTPException(
                status_code=404, detail=description
            )
    return result


async def get_active_object_model_or_404_and_validate_category(
    model, model_id, db: AsyncSession, model_category
):
    product = await get_active_object_model_or_404(model, model_id, db)
    await validate_category(
        category=model_category,
        category_id=product.category_id,
        db=db
    )
    return product


async def update_grade_product(product, db: AsyncSession):
    """Функция обновления рейтинга продукта"""
    product_raiting = await db.execute(
        select(func.avg(ReviewModel.grade)).where(
            ReviewModel.product_id == product.id,
            ReviewModel.is_active == True
        )
    )
    avg_rating = product_raiting.scalar() or 0.0
    product.rating = avg_rating
    await db.commit()


def get_validators_filters(kwargs: dict):
    if (
        kwargs.get('min_price') is not None
        and kwargs.get('max_price') is not None
        and kwargs['min_price'] > kwargs['max_price']
    ):
        raise HTTPException(
            status_code=400,
            detail="min_price не может быть больше max_price",
        )
    filters = []
    if kwargs.get('category_id') is not None:
        filters.append(ProductModel.category_id == kwargs['category_id'])
    if kwargs.get('min_price') is not None:
        filters.append(ProductModel.price >= kwargs['min_price'])
    if kwargs.get('max_price') is not None:
        filters.append(ProductModel.price <= kwargs['max_price'])
    if kwargs.get('in_stock') is not None:
        filters.append(
            ProductModel.stock > 0
            if kwargs['in_stock']
            else
            ProductModel.stock == 0
        )
    if kwargs.get('seller_id', None) is not None:
        filters.append(ProductModel.seller_id == kwargs['seller_id'])
    if kwargs.get('is_active') is not None:
        filters.append(ProductModel.is_active == kwargs['is_active'])
    return filters


async def _get_cart_item(
    db: AsyncSession,
    user_id: int,
    product_id: int,
):
    result = await db.scalars(
        select(CartItemModel)
        .options(selectinload(CartItemModel.product))
        .where(
            CartItemModel.user_id == user_id,
            CartItemModel.product_id == product_id,
        )
    )
    return result.first()


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


def get_list_order_item_id_done(done_orders):
    """
    Функция по извлечению имен из списка успешно завершенных задач
    от asyncio.wait с преобразованием их в числа
    """
    order_item_id_done = []
    for order_item in done_orders:
        if order_item.exception() is None:
            order_item_id_done.append(int(order_item.get_name()))
    return order_item_id_done


async def save_product_image(file: UploadFile) -> str:
    """
    Сохраняет изображение товара и возвращает URL,
    по которому это изображение будет доступно через веб-сервер
    """

    # Мы сравниваем MIME-тип, который клиент отправляет
    # в заголовке Content-Type с жёстко заданным белым списком
    # из conf.ALLOWED_IMAGE_TYPES
    if file.content_type not in conf.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Only JPG, PNG or WebP images are allowed"
        )

    # асинхронно читаем содержимое файла
    content = await file.read()

    # проверяется размер считанного файла
    if len(content) > conf.MAX_IMAGE_SIZE:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Image is too large")

    # извлекаем расширение из оригинального имени файла
    extension = Path(file.filename or "").suffix.lower() or ".jpg"

    # генерируем уникальное имя файла через uuid.uuid4(),
    # к которому добавляем расширение из переменной
    file_name = f"{uuid.uuid4()}{extension}"
    file_path = conf.MEDIA_ROOT / file_name

    # бинарная запись файла на диск
    file_path.write_bytes(content)

    return (
        f'/{conf.DIRECTORY_USER_CONTENT}/{conf.DIRECTORY_IMAGE_PRODUCTS}'
        f'/{file_name}'
    )


def remove_product_image(url: str | None) -> None:
    """
    Удаляет файл изображения, если он существует.
    """
    if not url:
        return
    relative_path = url.lstrip("/")
    file_path = conf.BASE_DIR / relative_path
    if file_path.exists():
        file_path.unlink()
