from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import Field, ConfigDict
from typing import Optional

import app.constants as c
from app.models.products import Product as ProductModel


class ProductFilter(Filter):
    """Фильтр для модели Product"""
    name__in: Optional[list[str]] = Field(alias="names", default=None)
    description__ilike: Optional[str] = Field(default=None)
    price__lte: Optional[float] = Field(
        ge=c.PRODUCT_MIN_PRICE, default=None
    )
    stock__gte: Optional[int] = Field(
        ge=c.PRODUCT_MIN_STOCK, default=None
    )
    rating__gte: Optional[float] = Field(
        ge=c.PRODUCT_MIN_RAITENG,
        le=c.PRODUCT_FILTER_MAX_RAITENG,
        default=None
    )
    seller_id: Optional[int] = Field(
        ge=c.PRODUCT_FILTER_MIN_VALUE_ID_SELLER,
        default=None
    )

    model_config = ConfigDict(populate_by_name=True)

    class Constants(Filter.Constants):
        model = ProductModel
