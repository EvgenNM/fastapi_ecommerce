from sqlalchemy import ForeignKey, String, Boolean, Float, Integer
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
