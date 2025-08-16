from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse

from asgi_correlation_id import CorrelationIdMiddleware

from config import get_settings

from app.core.startup import lifespan
from app.core.utils import LoggingMiddleware
from app.auth.routes import auth_router
from app.admin.routes import admin_router

settings = get_settings()

app = FastAPI(
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.SHOW_DOCS else None,
)

app.include_router(auth_router)
app.include_router(admin_router)


# https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)


@app.get("", include_in_schema=False)
@app.get("/", include_in_schema=False)
def docs_redirect():
    if settings.SHOW_DOCS:
        return RedirectResponse(url="/docs")
    else:
        return HTMLResponse("<h1>API Server Running</h1>")
