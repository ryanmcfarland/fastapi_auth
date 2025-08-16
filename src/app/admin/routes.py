import logging

from fastapi import APIRouter, Depends

from app.core.db import AsyncDatabase
from app.core.utils import ErrorHandlerRoute

from app.core.dependancies import get_db
from app.auth.dependancies import require_admin

log = logging.getLogger("admin.routes")

# `dependencies`
# -> Run this function before every route, but routes can't access the return value
# -> useful in this case because I don't need the current_user, only to check if the user is `admin`
admin_router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    route_class=ErrorHandlerRoute,
)


@admin_router.get("/database/pool_stats")
def pool_stats(database: AsyncDatabase = Depends(get_db)):
    return database.pool_stats


@admin_router.get("/database/health_check")
async def health_check(database: AsyncDatabase = Depends(get_db)):
    log.info("[admin.health_check] Checking database status")
    await database.health_check()
