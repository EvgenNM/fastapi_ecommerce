from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Boolean, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

import app.constants as c
from app.database import Base


class Review(Base):
    __tablename__ = 'reviews'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"), nullable=False
    )
    comment: Mapped[str | None] = mapped_column(
        String(c.REVIEW_COMMENT_MAX_LENGTH), nullable=True
    )
    comment_date: Mapped[datetime] = mapped_column(default=datetime.now)
    grade: Mapped[int] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product: Mapped['Product'] = relationship(
        'Product', back_populates='reviews'
    )
    user: Mapped['User'] = relationship(
        'User', back_populates='reviews'
    )

    __table_args__ = (
        CheckConstraint(
            f'grade >= {c.REVIEW_GRADE_MIN_VALUE} AND '
            f'grade <= {c.REVIEW_GRADE_MAX_VALUE}'
        ),
    )
