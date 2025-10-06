from typing import Optional
from sqlalchemy import ForeignKey, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Для запуска файла (не видит иначе app)
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.database import Base


# Проблема с цикличными импортами, Лучше всего все модели в один файл


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="category"
    )

    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True
    )
    parent: Mapped[Optional["Category"]] = relationship(
        "Category",
        back_populates="children",
        remote_side="Category.id"
    )
    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent"
    )


# if __name__ == "__main__":
#     from sqlalchemy.schema import CreateTable
    # from app.models.products import Product

    # print(CreateTable(Category.__table__))
    # print(CreateTable(Product.__table__))