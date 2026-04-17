from typing import Annotated

from fastapi import Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.mongodb import get_database
from app.repositories.car_repository import CarRepository
from app.services.car_service import CarService

DatabaseDep = Annotated[AsyncIOMotorDatabase, Depends(get_database)]


def get_car_repository(db: DatabaseDep) -> CarRepository:
    return CarRepository(db)


def get_car_service(repository: Annotated[CarRepository, Depends(get_car_repository)]) -> CarService:
    return CarService(repository)
