from datetime import datetime
from decimal import Decimal
from sqlalchemy import ForeignKey, Integer, Numeric, DateTime, func, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime

import app.constants as c
from app.database import Base
from app.models.products import Product

class OrderItem(Base):
    __tablename__ = "order_items"

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id"), primary_key=True, index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), primary_key=True, index=True
    )

    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="items")


class Order(Base):
    __tablename__ = 'orders'

    id: Mapped[int] = mapped_column(primary_key=True)
    # order_date: Mapped[datetime] = mapped_column(default=datetime.now)
    order_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=True
    )
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    buyer_id: Mapped[int]
    status: Mapped[str | None] = mapped_column(
        String(c.ORDER_STATUS_LENGTH_MAX),
        default=c.ORDER_DEFAULT_STATUS,
        nullable=True
    )

    products: Mapped[list["Product"]] = relationship(
        "Product",
        secondary="order_items",
        back_populates="orders",
        viewonly=True,
    )
    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        single_parent=True,
    )
