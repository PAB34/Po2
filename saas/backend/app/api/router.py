from fastapi import APIRouter

from app.api.routes.auth import router as auth_router
from app.api.routes.billing import router as billing_router
from app.api.routes.buildings import router as buildings_router
from app.api.routes.cities import router as cities_router
from app.api.routes.energie import router as energie_router
from app.api.routes.enedis_sync import router as enedis_sync_router
from app.api.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(billing_router, prefix="/api")
api_router.include_router(buildings_router, prefix="/api")
api_router.include_router(cities_router, prefix="/api")
# enedis_sync must be mounted before energie so /energie/sync/... is not caught by /energie/{prm_id}
api_router.include_router(enedis_sync_router, prefix="/api")
api_router.include_router(energie_router, prefix="/api")
api_router.include_router(health_router, prefix="/api")
