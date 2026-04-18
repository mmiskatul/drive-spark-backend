from typing import Annotated

from fastapi import APIRouter, Depends, File, Query, UploadFile, status

from app.api.dependencies import PartnerOrAdminDep, get_car_service
from app.schemas.car import CarCreate, CarImageUploadRead, CarRead, CarUpdate
from app.schemas.common import PaginatedResponse
from app.services.car_service import CarService
from app.services.cloudinary_service import upload_car_image

router = APIRouter()
CarServiceDep = Annotated[CarService, Depends(get_car_service)]
ImageFileDep = Annotated[UploadFile, File()]


@router.get("", response_model=PaginatedResponse[CarRead])
async def list_cars(
    service: CarServiceDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=12, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2),
) -> PaginatedResponse[CarRead]:
    return await service.list_cars(page=page, limit=limit, search=search)


@router.post("", response_model=CarRead, status_code=status.HTTP_201_CREATED)
async def create_car(
    payload: CarCreate,
    service: CarServiceDep,
    current_user: PartnerOrAdminDep,
) -> CarRead:
    partner_id = current_user.id if current_user.role == "partner" else None
    return await service.create_partner_car(payload, partner_id)


@router.post("/images", response_model=CarImageUploadRead)
async def upload_car_listing_image(
    current_user: PartnerOrAdminDep,
    file: ImageFileDep,
) -> CarImageUploadRead:
    del current_user
    uploaded = await upload_car_image(file)
    return CarImageUploadRead(url=uploaded.url, public_id=uploaded.public_id)


@router.get("/mine", response_model=PaginatedResponse[CarRead])
async def list_my_cars(
    service: CarServiceDep,
    current_user: PartnerOrAdminDep,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=100, ge=1, le=100),
    search: str | None = Query(default=None, min_length=2),
) -> PaginatedResponse[CarRead]:
    if current_user.role == "admin":
        return await service.list_cars(page=page, limit=limit, search=search)

    return await service.list_partner_cars(
        partner_id=current_user.id,
        page=page,
        limit=limit,
        search=search,
    )


@router.get("/{car_id}", response_model=CarRead)
async def get_car(car_id: str, service: CarServiceDep) -> CarRead:
    return await service.get_car(car_id)


@router.patch("/{car_id}", response_model=CarRead)
async def update_car(
    car_id: str,
    payload: CarUpdate,
    service: CarServiceDep,
    current_user: PartnerOrAdminDep,
) -> CarRead:
    await service.assert_can_manage_car(car_id, current_user.id, current_user.role)
    return await service.update_car(car_id, payload)


@router.post("/{car_id}/images", response_model=CarRead)
async def upload_existing_car_image(
    car_id: str,
    service: CarServiceDep,
    current_user: PartnerOrAdminDep,
    file: ImageFileDep,
) -> CarRead:
    await service.assert_can_manage_car(car_id, current_user.id, current_user.role)
    uploaded = await upload_car_image(file)
    return await service.add_car_image(car_id, uploaded.url)


@router.delete("/{car_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_car(
    car_id: str,
    service: CarServiceDep,
    current_user: PartnerOrAdminDep,
) -> None:
    await service.assert_can_manage_car(car_id, current_user.id, current_user.role)
    await service.delete_car(car_id)
