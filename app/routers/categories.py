from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categories import Category as CategoryModel
from app.schemas import Category as CategorySchema, CategoryCreate
from app.db_depends import get_async_db, get_db
from .validators import validate_category
from .tools import create_object_model, update_object_model


router = APIRouter(
    prefix="/categories",
    tags=["categories"],
)


@router.get("/", response_model=list[CategorySchema])
async def get_all_categories(db: AsyncSession = Depends(get_async_db)):
    """
    Возвращает список всех активных категорий.
    """
    stmt = select(CategoryModel).where(
        CategoryModel.is_active == True
    )
    result = await db.scalars(stmt)
    categories = result.all()
    return categories


@router.post(
        "/",
        response_model=CategorySchema,
        status_code=status.HTTP_201_CREATED
)
async def create_category(
    category: CategoryCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Создаёт новую категорию.
    """
    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        validate_category(
            CategoryModel, category.parent_id, db
        )
    db_category = await create_object_model(
        CategoryModel, category.model_dump(), db
    )
    return db_category


@router.put("/{category_id}", response_model=CategorySchema)
async def update_category(
    category_id: int,
    category: CategoryCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Обновляет категорию по её ID.
    """
    update_category = await validate_category(CategoryModel, category_id, db)
    # Проверка существования parent_id, если указан
    if category.parent_id is not None:
        await validate_category(CategoryModel, category.parent_id, db)
        if category.parent_id == category_id:
            raise HTTPException(
                status_code=400, detail="Category cannot be its own parent"
            )

    # Обновление категории
    db_category = await update_object_model(
        CategoryModel,
        update_category,
        category.model_dump(),
        db
    )
    return db_category


@router.delete("/{category_id}", status_code=status.HTTP_200_OK)
async def delete_category(
    category_id: int, db: AsyncSession = Depends(get_async_db)
):
    """
    Логически удаляет категорию по её ID, устанавливая is_active=False.
    """
    # Проверка существования активной категории
    update_category = await validate_category(CategoryModel, category_id, db)
    await update_object_model(
            CategoryModel, update_category, {'is_active': False}, db
        )
    return {"status": "success", "message": "Категория перестала быть активной"}
