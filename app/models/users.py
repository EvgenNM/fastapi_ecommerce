from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

import app.constants as c
from app.database import Base
from app.models.profiles import Profile


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    role: Mapped[str] = mapped_column(String, default=c.USER_NAME_ROLE_BUYER)

    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="seller"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="user"
    )

    profile: Mapped["Profile"] = relationship(
        "Profile", back_populates="user", uselist=False
    )
