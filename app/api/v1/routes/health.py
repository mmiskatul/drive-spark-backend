from fastapi import APIRouter

from app.api.dependencies import DatabaseDep
from app.schemas.health import HealthCheck

router = APIRouter()


@router.get("/health", response_model=HealthCheck)
async def health_check(db: DatabaseDep) -> HealthCheck:
    await db.command("ping")
    return HealthCheck(status="ok", database="ok")
