import os
import uuid
import urllib
from decimal import Decimal
from pathlib import Path

import aiofiles
import aiohttp
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
from .validators import (
    validate_category,
    validate_content_type,
    validate_extension,
    validate_size
)


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
    model, object_model, values: dict, db: AsyncSession
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


async def create_and_get_link_from_yandex_disk(
    image,
    file_name,
    session
):
    payload = {
        # Загрузить файл с названием file_name в папку приложения.
        'path': f'app:/{file_name}',
        # перезапись существующего файла
        'overwrite': 'True'
    }
    # Получение ссылки для загрузки файла
    async with session.get(
        url=conf.REQUEST_UPLOAD_URL,
        # Заголовок для авторизации
        headers=conf.AUTH_HEADERS,
        # Параметры файла
        params=payload
    ) as response:
        upload_url = (await response.json())['href']

    # Процесс сохранения файла
    async with session.put(
        data=image,
        url=upload_url
    ) as file_remember:
        # Получение расположения файла из Location
        location = file_remember.headers['Location']
        # Декодирование строки при помощи модуля urllib.
        location = urllib.parse.unquote(location)
        # Убираем первую часть расположения файла /disk,
        location = location.replace('/disk', '')

    async with session.get(
        url=conf.DOWNLOAD_LINK_URL,
        headers=conf.AUTH_HEADERS,
        params={'path': location}
    ) as file_link:

        link = (await file_link.json())['href']
    return link


def get_name_file_with_uuid4(extension: str):
    """
    Получение имени файла склеивая сгененрированную
    послед-ть uuid4() с переданным расширением (extension)
    """
    uuid_name = uuid.uuid4()
    file_name = f"{uuid_name}{extension}"
    return file_name


def validate_file_and_get_file_name(file: UploadFile):
    # Валидация MIME-типа, отправляемого клиентом
    validate_content_type(file)

    # извлекаем расширение из оригинального имени файла
    extension = Path(file.filename or "").suffix.lower() or ".jpg"

    # Валидация расширения из оригинального имени файла
    validate_extension(extension)
    # Формирование имени файла на основе uuid4() и расширения (extension)
    file_name = get_name_file_with_uuid4(extension)

    return file_name


async def save_product_image_on_disk(
        file: UploadFile,
        session: aiohttp.ClientSession
):
    """
    Сохраняет на яндекс диске изображение товара и возвращает
    URL для его скачивания, а также имя файла с которым оно будет сохранено
    в объекте модели Image
    """

    # Формирование имени файла и его валидация
    file_name = validate_file_and_get_file_name(file)
    # установка счетчика для измерения размера загружаемого файла
    current_size = 0
    # создаем список для чанок
    chanks = []
    try:
        while content := await file.read(conf.CHANK_SIZE):
            # Увеличиваем счетчик прочитанного размера
            current_size += len(content)
            # Валидация размера файла
            validate_size(current_size)
            # добавление чанка в список
            chanks.append(content)
        # Склейка чанков в бинарный файл
        b_image = b''.join(chanks)
        # Сохранение на яндекс диске изображения с получением
        # ссылки для его скачивания
        link = await create_and_get_link_from_yandex_disk(
            b_image,
            file_name,
            session
        )
    except Exception as e:
        # Общая обработка возможных ошибок (например, проблем с диском)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during file upload: {e}"
        )

    return [link, file_name]


async def save_product_image(file: UploadFile, session=None):
    """
    Сохраняет на локальной машине изображение товара и возвращает
    URL с которым оно будет доступно для скачивания,
    а также имя файла с которым оно будет сохранено
    в объекте модели Image
    """
    # Формирование имени файла и его валидация
    file_name = validate_file_and_get_file_name(file)
    # Формирование адреса сохранения файла
    file_path = conf.MEDIA_ROOT / file_name
    # установка счетчика для измерения размера загружаемого файла
    current_size = 0
    try:
        # Открываем файл для асинхронной записи на диск
        async with aiofiles.open(file_path, "wb") as out_file:
            # Читаем файл по частям
            while content := await file.read(conf.CHANK_SIZE):
                # Увеличиваем счетчик прочитанного размера
                current_size += len(content)
                # Валидация размера файла
                validate_size(current_size)
                # Асинхронная запись чанка в файл
                await out_file.write(content)
            # Формирование готовой ссылки для скачивания
            link = (
                f'/{conf.DIRECTORY_USER_CONTENT}/'
                f'{conf.DIRECTORY_IMAGE_PRODUCTS}'
                f'/{file_name}'
            )

    except HTTPException:
        # Если HTTPException был поднят из-за размера файла,
        # нам нужно удалить частично загруженный файл,
        # чтобы FastAPI мог его обработать и отправить клиенту.
        if file_path:
            os.remove(file_path)  # Удаляем неполный файл
        raise  # Повторно выбрасываем исключение
    except Exception as e:
        # Общая обработка других возможных ошибок (например, проблем с диском)
        if file_path:
            os.remove(file_path)  # Удаляем неполный файл
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during file upload: {e}"
        )

    return [link, file_name]


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
