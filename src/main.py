from fastapi import FastAPI
from fastapi.responses import RedirectResponse, HTMLResponse

from asgi_correlation_id import CorrelationIdMiddleware

from config import get_settings

from app.api.startup import lifespan
from app.api.middleware import LoggingMiddleware
from app.auth.middleware import AuthNoStoreMiddleware

from app.auth.routes import auth_router
from app.admin.routes import admin_router

settings = get_settings()

app = FastAPI(
    lifespan=lifespan,
    openapi_url="/openapi.json" if settings.show_docs else None,
)

app.include_router(auth_router)
app.include_router(admin_router)


# https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthNoStoreMiddleware)
app.add_middleware(CorrelationIdMiddleware)


@app.get("", include_in_schema=False)
@app.get("/", include_in_schema=False)
def docs_redirect():
    if settings.show_docs:
        return RedirectResponse(url="/docs")
    else:
        return HTMLResponse("<h1>API Server Running</h1>")
