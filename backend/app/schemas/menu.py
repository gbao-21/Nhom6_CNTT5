"""Schemas cho dữ liệu thực đơn tổng hợp."""
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.dish import DishResponse


class MenuCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool
    dishes: list[DishResponse] = Field(default_factory=list)


class MenuDishListResponse(BaseModel):
    items: list[DishResponse]
    total: int
    page: int
    page_size: int


class MenuOverviewResponse(BaseModel):
    categories: list[MenuCategoryResponse]
