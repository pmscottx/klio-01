from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.config import settings, load_remote_config, register_service, deregister_service
from app.database import make_engine, make_session_factory, create_tables
from app import events
from app.seed import seed_db

engine = None
session_factory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global engine, session_factory
    await load_remote_config()
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    await create_tables(engine)
    async with session_factory() as db:
        await seed_db(db)
    await events.connect()
    events.start_consumer_task(session_factory)
    await register_service()
    yield
    await deregister_service()
    await events.disconnect()
    await engine.dispose()


app = FastAPI(title="DBValidator Service", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "up", "service": "dbvalidator-service"}
