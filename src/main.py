from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import RedirectResponse

from asgi_correlation_id import CorrelationIdMiddleware

from app.core.db import AsyncDatabase
from app.core.startup import lifespan
from app.core.dependancies import get_db
from app.core.utils import LoggingMiddleware

from app.auth.dependancies import require_role
from app.auth.routes import auth_router

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router)


# https://fastapi.tiangolo.com/tutorial/middleware/#multiple-middleware-execution-order
app.add_middleware(LoggingMiddleware)
app.add_middleware(CorrelationIdMiddleware)


@app.get("", include_in_schema=False)
@app.get("/", include_in_schema=False)
async def docs_redirect():
    return RedirectResponse(url="/docs")


@app.post("/protected")
async def test_me(user=Depends(require_role("test_role"))):
    return user


@app.get("/users/{user_id}")
async def get_user(user_id: int, database: AsyncDatabase = Depends(get_db)):
    """Example endpoint using the database."""
    user = await database.fetchone("SELECT id, username, email FROM users WHERE id = %s", [user_id])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
