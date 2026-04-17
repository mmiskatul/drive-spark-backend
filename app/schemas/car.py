from datetime import datetime

from pydantic import BaseModel, Field

from app.models.car import CarStatus


class CarBase(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    brand: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1990, le=2100)
    category: str = Field(min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=160)
    price_per_day: float = Field(gt=0)
    seats: int = Field(ge=1, le=12)
    transmission: str = Field(min_length=2, max_length=40)
    fuel: str = Field(min_length=2, max_length=40)
    features: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None, max_length=2000)


class CarCreate(CarBase):
    status: CarStatus = CarStatus.ACTIVE


class CarUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    brand: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1990, le=2100)
    category: str | None = Field(default=None, min_length=2, max_length=60)
    location: str | None = Field(default=None, min_length=2, max_length=160)
    price_per_day: float | None = Field(default=None, gt=0)
    seats: int | None = Field(default=None, ge=1, le=12)
    transmission: str | None = Field(default=None, min_length=2, max_length=40)
    fuel: str | None = Field(default=None, min_length=2, max_length=40)
    status: CarStatus | None = None
    features: list[str] | None = None
    description: str | None = Field(default=None, max_length=2000)


class CarRead(CarBase):
    id: str
    slug: str
    status: CarStatus
    created_at: datetime
    updated_at: datetime
