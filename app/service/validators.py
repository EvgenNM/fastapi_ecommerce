from fastapi import HTTPException, status, UploadFile
from sqlalchemy import select

import app.config as conf


async def validate_category(category, category_id, db):
    """
    Проверка существования категории
    """
    stmt = select(category).where(
            category.id == category_id,
            category.is_active == True
        )
    result = await db.scalars(stmt)
    category = result.first()
    if category is None:
        raise HTTPException(
            status_code=400, detail="Category not found"
        )
    return category


async def validate_one_review(model, user_id, db):
    """Валидация для модели ReviewModel по полю user_id"""
    model_objects = await db.scalars(select(model).where(
            model.user_id == user_id,
            model.is_active == True
        )
    )
    if model_objects.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Только один отзыв можно оставить на товар'
        )


def validate_content_type(file: UploadFile):
    # Мы сравниваем MIME-тип, который клиент отправляет
    # в заголовке Content-Type с жёстко заданным белым списком
    # из conf.ALLOWED_IMAGE_TYPES
    if file.content_type not in conf.ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            (
                f"Only {', '.join(conf.ALLOWED_FILE_EXTENSIONS)} "
                "images are allowed"
            )
        )


def validate_extension(extension: str):
    # Валидация расширения из оригинального имени файла
    if extension not in conf.ALLOWED_FILE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported file extension: '{extension}'. Only "
                f"{', '.join(conf.ALLOWED_FILE_EXTENSIONS)} are allowed."
            )
        )


def validate_size(current_size):
    # --- Логика валидации размера ---
    if current_size > conf.MAX_IMAGE_SIZE:
        # Если текущий размер превысил лимит, немедленно прерываем
        # и генерируем исключение HTTPException.
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            # Статус 413 указывает на слишком большой размер
            detail=(
                f"File too large. Max size is"
                f"{conf.MAX_IMAGE_SIZE} B."
            )
        )