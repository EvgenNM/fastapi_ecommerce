from datetime import datetime

from sqlalchemy import (
    ForeignKey, String, Boolean, DateTime, Float, Computed, Integer, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

import app.constants as c
from app.database import Base


class Image(Base):
    __tablename__ = "images"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(
        nullable=False
    )
    title_url: Mapped[str] = mapped_column(
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )

    product: Mapped["Product"]= relationship(back_populates="images")
