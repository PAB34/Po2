from fastapi import APIRouter

from app.api.routes.accounting_matrix import router as accounting_matrix_router
from app.api.routes.auth import router as auth_router
from app.api.routes.cpe import router as cpe_router
from app.api.routes.cpe_dalkia import router as cpe_dalkia_router
from app.api.routes.billing import router as billing_router
from app.api.routes.bpu import router as bpu_router
from app.api.routes.buildings import router as buildings_router
from app.api.routes.cities import router as cities_router
from app.api.routes.cvc import router as cvc_router
from app.api.routes.enedis_async import router as enedis_async_router
from app.api.routes.equipment import router as equipment_router
from app.api.routes.engie import router as engie_router
from app.api.routes.engie_budget import router as engie_budget_router
from app.api.routes.gas_budget import router as gas_budget_router
from app.api.routes.gas_invoice import router as gas_invoice_router
from app.api.routes.marches import router as marches_router
from app.api.routes.grdf import router as grdf_router
from app.api.routes.energie import router as energie_router
from app.api.routes.enedis_sync import router as enedis_sync_router
from app.api.routes.health import router as health_router
from app.api.routes.internal_auth import router as internal_auth_router
from app.api.routes.patrimoine_match import router as patrimoine_match_router
from app.api.routes.pronostics import router as pronostics_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/api")
api_router.include_router(internal_auth_router, prefix="/api")
api_router.include_router(pronostics_router, prefix="/api")
api_router.include_router(billing_router, prefix="/api")
api_router.include_router(bpu_router, prefix="/api")
api_router.include_router(buildings_router, prefix="/api")
api_router.include_router(patrimoine_match_router, prefix="/api")
api_router.include_router(cities_router, prefix="/api")
api_router.include_router(cvc_router, prefix="/api")
# enedis_async + enedis_sync must be mounted before energie so /energie/sync/... is not caught by /energie/{prm_id}
api_router.include_router(enedis_async_router, prefix="/api")
api_router.include_router(enedis_sync_router, prefix="/api")
api_router.include_router(engie_router, prefix="/api")
api_router.include_router(gas_invoice_router, prefix="/api")
api_router.include_router(gas_budget_router, prefix="/api")
api_router.include_router(engie_budget_router, prefix="/api")
api_router.include_router(grdf_router, prefix="/api")
api_router.include_router(energie_router, prefix="/api")
api_router.include_router(equipment_router, prefix="/api")
api_router.include_router(cpe_router, prefix="/api")
api_router.include_router(cpe_dalkia_router, prefix="/api")
api_router.include_router(accounting_matrix_router, prefix="/api")
api_router.include_router(marches_router, prefix="/api")
api_router.include_router(health_router, prefix="/api")
