from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, field_validator


class MenuDishOptionOut(BaseModel):
    id: int
    dish_id: int
    name: str
    price: Decimal
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


class MenuOptionGroupOut(BaseModel):
    group_name: str
    is_required: bool = False
    min_choices: int = 0
    max_choices: int = 10
    items: List[MenuDishOptionOut] = []


class MenuCategoryBriefOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class MenuDishOut(BaseModel):
    id: int
    category_id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: Decimal
    image_url: Optional[str] = None
    is_available: bool
    sold_count: int = 0
    rating: float = 5.0
    options: List[MenuDishOptionOut] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator("options", mode="before")
    @classmethod
    def filter_available_options(cls, v):
        if not v:
            return []
        return [opt for opt in v if getattr(opt, "is_available", True)]


class MenuDishDetailOut(MenuDishOut):
    category: Optional[MenuCategoryBriefOut] = None
    option_groups: List[MenuOptionGroupOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedMenuDishesOut(BaseModel):
    items: List[MenuDishOut]
    total: int
    page: int
    page_size: int
    total_pages: int


class MenuCategoryWithDishesOut(MenuCategoryBriefOut):
    dishes: List[MenuDishOut] = []

    model_config = ConfigDict(from_attributes=True)


class CustomerMenuOverviewOut(BaseModel):
    categories: List[MenuCategoryWithDishesOut]
    total_categories: int
    total_dishes: int