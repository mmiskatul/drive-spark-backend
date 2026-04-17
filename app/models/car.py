from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.base import PyObjectId


class CarStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    UNAVAILABLE = "unavailable"


class CarDocument(BaseModel):
    id: PyObjectId | None = Field(default=None, alias="_id")
    title: str
    slug: str
    brand: str
    model: str
    year: int
    category: str
    location: str
    price_per_day: float
    seats: int
    transmission: str
    fuel: str
    status: CarStatus = CarStatus.ACTIVE
    features: list[str] = Field(default_factory=list)
    description: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"populate_by_name": True}
