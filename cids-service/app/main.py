from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings, load_remote_config, register_service, deregister_service
from app.database import make_engine, make_session_factory, create_tables
from app.routes import router

engine = None
session_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, session_factory
    await load_remote_config()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    await create_tables(engine)
    await register_service()
    yield
    await deregister_service()
    await engine.dispose()


app = FastAPI(title="CIDS Service", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "up", "service": "cids-service"}
