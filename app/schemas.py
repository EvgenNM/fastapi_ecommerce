from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional


class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: str = Field(
        min_length=3,
        max_length=50,
        description="Название категории (3-50 символов)"
    )
    parent_id: Optional[int] = Field(
        None,
        description="ID родительской категории, если есть"
    )


class Category(CategoryCreate):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор категории")
    is_active: bool = Field(description="Активность категории")

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """
    name: str = Field(
        min_length=3,
        max_length=100,
        description="Название товара (3-100 символов)"
    )
    description: Optional[str] = Field(
        None,
        max_length=500,
        description="Описание товара (до 500 символов)"
    )
    price: float = Field(gt=0, description="Цена товара (больше 0)")
    image_url: Optional[str] = Field(
        None,
        max_length=200, description="URL изображения товара"
    )
    stock: int = Field(
        ge=0,
        description="Количество товара на складе (0 или больше)"
    )
    category_id: int = Field(
        description="ID категории, к которой относится товар"
    )
    seller_id: int = Field()


class Product(ProductCreate):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """
    id: int = Field(description="Уникальный идентификатор товара")
    is_active: bool = Field(description="Активность товара")

    model_config = ConfigDict(from_attributes=True)


class BaseUser(BaseModel):
    email: EmailStr = Field(description="Email пользователя")
    role: str = Field(
        default="buyer",
        pattern="^(buyer|seller)$",
        description="Роль: 'buyer' или 'seller'"
    )


class UserCreate(BaseUser):
    password: str = Field(
        min_length=8, description="Пароль (минимум 8 символов)"
    )


class User(BaseUser):
    id: int
    model_config = ConfigDict(from_attributes=True)
