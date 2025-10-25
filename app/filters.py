from datetime import datetime

from fastapi_filter import FilterDepends
from fastapi_filter.contrib.sqlalchemy import Filter
from pydantic import Field, ConfigDict
from typing import Optional


from app.models.products import Product as ProductModel


class ProductFilter(Filter):
    """Фильтр для модели Product"""
    name__in: Optional[list[str]] = Field(alias="names", default=None)
    description__ilike: Optional[str] = Field(default=None)
    price__lte: Optional[float] = Field(ge=0.0, default=None)
    stock__gte: Optional[int] = Field(ge=0, default=None)
    rating__gte: Optional[float] = Field(ge=0, le=5, default=None)
    seller_id: Optional[int] = Field(ge=1, default=None)

    model_config = ConfigDict(populate_by_name=True)

    class Constants(Filter.Constants):
        model = ProductModel
