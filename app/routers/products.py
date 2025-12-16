import asyncio
from pathlib import Path

import aiohttp
from fastapi import (
    APIRouter, Depends, HTTPException, status,
    Query, UploadFile, File, Form
)
from fastapi_filter import FilterDepends
from sqlalchemy import desc, func, select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import app.constants as c
import app.config as conf
from app.auth import get_current_seller
from app.db_depends import get_async_db
from app.filters import ProductFilter
from app.models.images import Image
from app.models.products import Product as ProductModel
from app.models.categories import Category as CategoryModel
from app.models.users import User as UserModel
from app.schemas import Product as ProductSchema, ProductCreate, ProductList
from app.service.validators import validate_category
from app.service.tools import (
    create_object_model,
    update_object_model,
    get_active_object_model_or_404_and_validate_category,
    get_validators_filters,
    save_product_image,
    remove_product_image,
    save_product_image_on_disk
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MEDIA_ROOT = BASE_DIR / "media" / "products"
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE = 2 * 1024 * 1024

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
        search: str | None = Query(
            None,
            min_length=1,
            description="Поиск по названию/описанию"
        ),
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

    rank_col = None

    if search:
        search_value = search.strip()
        if search_value:
            # строим два tsquery для одной и той же фразы
            # websearch_to_tsquery понимает сложные конструкции:
            # кавычки для точных фраз, OR, - для исключения слов
            # 'english' и 'russian' - это названия конфигураций текст-го поиска
            ts_query_en = func.websearch_to_tsquery('english', search_value)
            ts_query_ru = func.websearch_to_tsquery('russian', search_value)

            # Ищем совпадение в любой конфигурации и добавляем в общий фильтр
            ts_match_any = or_(
                # ProductModel.tsv - поле типа tsvector в таблице товаров,
                # которое содержит предварительно обработанный текст
                # Оператор @@ - спец. оператор PostgreSQL для проверки
                # соответствия между tsvector и tsquery
                ProductModel.tsv.op('@@')(ts_query_en),
                ProductModel.tsv.op('@@')(ts_query_ru),
            )
            validators_filters.append(ts_match_any)

            # Эта часть отвечает за сортировку результатов по релевантности
            # func.greatest() - выбирает максимальное значение из двух рангов
            rank_col = func.greatest(
                # func.ts_rank_cd() - вычисляет ранг (релевантность) между
                # документом (tsvector) и запросом (tsquery)
                func.ts_rank_cd(ProductModel.tsv, ts_query_en),
                func.ts_rank_cd(ProductModel.tsv, ts_query_ru),
            ).label("rank")
            # .label("rank") - присв. псевдоним столбцу для дальнейш. использ-я

        # Вариант для поиска по одному языку
        # ts_query = func.websearch_to_tsquery('english', search_value)
        # validators_filters.append(ProductModel.tsv.op('@@')(ts_query))
        # rank_col = func.ts_rank_cd(ProductModel.tsv, ts_query).label("rank")

    total_stmt = select(func.count()).select_from(
        ProductModel
    ).where(*validators_filters)

    total = await db.scalar(total_stmt) or 0

    if rank_col is not None:
        products_stmt = (
            select(ProductModel, rank_col)
            .where(*validators_filters)
            .order_by(desc(rank_col), ProductModel.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await db.execute(products_stmt)
        items = [row[0] for row in result.all()]
        # сами объекты
        # при желании можно вернуть ранг в ответе
        # ranks = [row.rank for row in rows]
    else:
        products_stmt = (
            select(ProductModel)
            .where(*validators_filters)
            .options(selectinload(ProductModel.images))
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
    product: ProductCreate = Depends(ProductCreate.as_form),
    image: UploadFile | None = File(None),
    image_others: list[UploadFile] | None = File(
        default=None,
        description=f'Загрузите до {conf.MAX_COUNT_IMAGES} картинок'
    ),
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

    # Сохранение изображения (если есть)
    image_url = await save_product_image(image) if image else None

    # Сбор интересуемых значений (аргументов) модели Product
    values = product.model_dump() | {
        'seller_id': current_user.id,
        'image_url': image_url[0] if image_url else None
    }
    db_product = ProductModel(
        **values
    )
    db.add(db_product)

    # отправляет запрос в БД (получение ID модели Product)
    await db.flush()
    # проверка на наличие дополнительных изображений
    if image_others:
        async with aiohttp.ClientSession() as session:
            # Создание задач для потоковой загрузки
            tasks = [
                asyncio.create_task(
                    save_product_image_on_disk(image, session),
                    name=str(number)
                )
                for number, image in enumerate(
                    image_others[:conf.MAX_COUNT_IMAGES]
                )
            ]

            # асинхронные считывание чанками и сохранение файлов
            done_tasks, pending_tasks = await asyncio.wait(tasks)

            # формирование списка успешно сохраненных файлов
            saved_images = []
            for done_task in done_tasks:
                if done_task.exception() is None:
                    saved_images.append(done_task)

            if saved_images:
                saved_images.sort(key=lambda x: int(x.get_name()))

            # страховочное закрытие фоновых не завершенных задач
            for pending_task in pending_tasks:
                pending_task.cancel()

            # переключение для завершения задач выше, помеченных на удаление
            await asyncio.sleep(0)

            # создание объектов таблицы Image при наличии успешно
            # сохраненных картинок
            if saved_images:
                for saved_image in saved_images:
                    image_url, image_uuid = saved_image.result()
                    other_image_product = Image(
                        title=str(image_uuid),
                        title_url=image_url,
                        product_id=db_product.id
                    )
                    db.add(other_image_product)

    # Сохраняем все изменения в БД
    await db.commit()

    # получение объекта продукта
    # и добавленных дополнительных картинок
    product_scalars = await db.scalars(
        select(ProductModel)
        .options(selectinload(ProductModel.images))
        .where(
            ProductModel.id == db_product.id,
            ProductModel.is_active == True
        )
        .order_by(ProductModel.id)
    )
    db_product = product_scalars.first()
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
    product_update: ProductCreate = Depends(ProductCreate.as_form),
    image: UploadFile | None = File(None),
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

    image_url = await save_product_image(image) if image else None
    if product.image_url:
        remove_product_image(product.image_url)
    product = await update_object_model(
        ProductModel,
        product,
        product_update.model_dump() | {
            'image_url': image_url[0] if image_url else None
        },
        db
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
    remove_product_image(product.image_url)
    return {"status": "success", "message": "Product marked as inactive"}
