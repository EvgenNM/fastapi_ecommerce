from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional

import app.constants as c


class BaseFieldIdIsActive(BaseModel):
    id: int
    is_active: bool


class CategoryCreate(BaseModel):
    """
    Модель для создания и обновления категории.
    Используется в POST и PUT запросах.
    """
    name: str = Field(
        min_length=c.CATEGORY_NAME_MIN_LENGTCH,
        max_length=c.CATEGORY_NAME_MAX_LENGTCH,
        description=(
            f'Название категории ({c.CATEGORY_NAME_MIN_LENGTCH}-'
            f'{c.CATEGORY_NAME_MAX_LENGTCH} символов)'
        )
    )
    parent_id: Optional[int] = Field(
        None,
        description='ID родительской категории, если есть'
    )


class Category(CategoryCreate, BaseFieldIdIsActive):
    """
    Модель для ответа с данными категории.
    Используется в GET-запросах.
    """
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseModel):
    """
    Модель для создания и обновления товара.
    Используется в POST и PUT запросах.
    """
    name: str = Field(
        min_length=c.PRODUCT_NAME_MIN_LENGTCH,
        max_length=c.PRODUCT_NAME_MAX_LENGTCH,
        description=(
            f'Название товара ({c.PRODUCT_NAME_MIN_LENGTCH}-'
            f'{c.PRODUCT_NAME_MAX_LENGTCH} символов)'
        )
    )
    description: Optional[str] = Field(
        None,
        max_length=c.PRODUCT_DESCRIPTION_MAX_LENGTCH,
        description=(
            'Описание товара (до '
            f'{c.PRODUCT_DESCRIPTION_MAX_LENGTCH} символов)'
        )
    )
    price: float = Field(
        gt=c.PRODUCT_MIN_PRICE,
        description=f'Цена товара (больше {c.PRODUCT_MIN_PRICE})'
    )
    image_url: Optional[str] = Field(
        None,
        max_length=c.PRODUCT_MAX_LENGTH_IMAGE_URL,
        description='URL изображения товара'
    )
    stock: int = Field(
        ge=c.PRODUCT_MIN_STOCK,
        description=(
            f'Количество товара на складе ({c.PRODUCT_MIN_STOCK} или больше)'
        )
    )
    category_id: int = Field(
        description="ID категории, к которой относится товар"
    )
    seller_id: int = Field()


class Product(ProductCreate, BaseFieldIdIsActive):
    """
    Модель для ответа с данными товара.
    Используется в GET-запросах.
    """
    rating: Optional[float] = Field(None)

    model_config = ConfigDict(from_attributes=True)


class BaseUser(BaseModel):
    """
    Базовая модель для валидации юзеров и вывода о них информации
    """
    email: EmailStr = Field(description="Email пользователя")
    role: str = Field(
        default=c.USER_NAME_ROLE_BUYER,
        pattern=f'^({c.USER_NAME_ROLE_BUYER}|{c.USER_NAME_ROLE_SELLER})$',
        description=(
            f'Роль: "{c.USER_NAME_ROLE_BUYER}" или "{c.USER_NAME_ROLE_SELLER}"'
        )
    )


class ProfileCreate(BaseModel):
    avatar: Optional[str] = Field(None, max_length=100)
    city: Optional[str] = Field(None, max_length=100)
    country: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=1000)


class ProfileSchemas(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseUser):
    password: str = Field(
        min_length=c.USER_PASSWORD_MIN_LENGTH,
        description=f'Пароль (минимум {c.USER_PASSWORD_MIN_LENGTH} символов)'
    )


class User(BaseUser, BaseFieldIdIsActive):
    model_config = ConfigDict(from_attributes=True)


class UserRead(User):
    profile: Optional[ProfileSchemas] = None


class ReviewCreate(BaseModel):

    product_id: int = Field()
    comment: Optional[str] = Field(
        None, max_length=c.REVIEW_COMMENT_MAX_LENGTH
    )
    grade: int = Field(
        ge=c.REVIEW_GRADE_MIN_VALUE,
        le=c.REVIEW_GRADE_MAX_VALUE,
        description=(
            f'Оценка от {c.REVIEW_GRADE_MIN_VALUE} до '
            f'{c.REVIEW_GRADE_MAX_VALUE} баллов'
        )
    )


class Review(ReviewCreate, BaseFieldIdIsActive):

    comment_date: datetime = Field()
    is_active: bool = Field()

# class OrderItem(Base):
#     __tablename__ = "order_items"

#     order_id: Mapped[int] = mapped_column(
#         ForeignKey("orders.id"), primary_key=True, index=True
#     )
#     product_id: Mapped[int] = mapped_column(
#         ForeignKey("products.id"), primary_key=True, index=True
#     )

#     quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
#     price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

#     order: Mapped["Order"] = relationship(back_populates="items")
#     product: Mapped["Product"] = relationship(back_populates="items")


class OrderItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    order_id: int
    product_id: int

    quantity: int
    price: Decimal

    # order:
    product: Product
