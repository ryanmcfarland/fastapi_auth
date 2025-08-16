from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from asgi_correlation_id import CorrelationIdMiddleware

from app.core.startup import lifespan
from app.core.utils import LoggingMiddleware

from app.auth.routes import auth_router
from app.admin.routes import admin_router

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)
app.include_router(admin_router)


# https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)


@app.get("", include_in_schema=False)
@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")
