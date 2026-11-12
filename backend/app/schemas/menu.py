from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class MenuDishOptionOut(BaseModel):
    id: int
    dish_id: int
    name: str
    price: Decimal
    is_available: bool

    model_config = ConfigDict(from_attributes=True)


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
    options: List[MenuDishOptionOut] = []

    model_config = ConfigDict(from_attributes=True)


class MenuDishDetailOut(MenuDishOut):
    category: Optional[MenuCategoryBriefOut] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MenuCategoryWithDishesOut(MenuCategoryBriefOut):
    dishes: List[MenuDishOut] = []

    model_config = ConfigDict(from_attributes=True)


class CustomerMenuOverviewOut(BaseModel):
    categories: List[MenuCategoryWithDishesOut]
    total_categories: int
    total_dishes: int