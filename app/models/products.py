from sqlalchemy import (
    ForeignKey, String, Boolean, Float, Computed, Integer, Index
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

import app.constants as c
from app.database import Base


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(
        String(c.PRODUCT_NAME_MAX_LENGTCH), nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        String(c.PRODUCT_DESCRIPTION_MAX_LENGTCH), nullable=True
    )
    price: Mapped[float] = mapped_column(Float, nullable=False)
    image_url: Mapped[str | None] = mapped_column(
        String(c.PRODUCT_MAX_LENGTH_IMAGE_URL), nullable=True
    )
    stock: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), nullable=False
    )
    seller_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    rating: Mapped[float] = mapped_column(default=c.PRODUCT_MIN_RAITENG)

    category: Mapped["Category"] = relationship(back_populates="products")
    seller: Mapped["User"]= relationship(back_populates="products")
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates='product'
    )
    orders: Mapped[list['Order']] = relationship(
        'Order',
        secondary='order_items',
        back_populates='products',
        # Только для чтения
        viewonly=True
    )
    items: Mapped[list['OrderItem']] = relationship(
        back_populates='product',
        cascade='all, delete-orphan',
        single_parent=True,
    )
    cart_items: Mapped[list["CartItem"]] = relationship(
        "CartItem",
        back_populates="product", cascade="all, delete-orphan"
    )
    images: Mapped[list['Image']] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

    # вычисляемое поле tsv для поиска
    # (это встроенный движок полнотекстового поиска, работающий на уровне
    # базы данных и оптимизированный для высоконагруженных систем)
    tsv: Mapped[TSVECTOR] = mapped_column(
        TSVECTOR,
        # 1) устанавливаем setweight(..., 'A') и setweight(..., 'B').
        # (PostgreSQL FTS поддерживает 4 уровня весов: A > B > C > D)
        # 2) tsvector преобразует текст в инвертированный индекс (tsvector).
        # (Это добавляет поддержку морфологии соответ. языка)
        # 3) знач. '' позв. при name (description) = NULL исп-ть пустую строку
        Computed(
            """
            setweight(to_tsvector('english', coalesce(name, '')), 'A')
            ||
            setweight(to_tsvector('russian', coalesce(name, '')), 'A')
            ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B')
            ||
            setweight(to_tsvector('russian', coalesce(description, '')), 'B')
            """,
            persisted=True,
        ),
        nullable=False,
    )

    # Для поиска
    # GIN (Generalized Inverted Index) — специализ-й индекс для tsvector.
    # Скорость: поиск за O(1) даже на миллионах записей
    # Поддержка: морфология, веса, web-синтаксис
    # Размер: Довольно не большой (около 20-30% от размера текста)
    __table_args__ = (
        Index("ix_products_tsv_gin", "tsv", postgresql_using="gin"),
    )
