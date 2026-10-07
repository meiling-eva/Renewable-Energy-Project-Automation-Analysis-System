import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.config import CORS_ORIGINS
from app.database import Base, engine
from app.routers import compliance_checks, imports, projects


logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as e:
        logger.warning("Database unavailable; tables not created. Import previews still work. (%s)", e.orig)
    yield


app = FastAPI(title="Automation Process API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router, prefix="/api")
app.include_router(compliance_checks.router, prefix="/api")
app.include_router(imports.router, prefix="/api")


@app.get("/api/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError:
        return {"status": "ok", "database": "unavailable"}
    return {"status": "ok", "database": "connected"}
