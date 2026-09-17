from contextlib import asynccontextmanager

from fastapi import FastAPI

from maitri.init_db import init_db
from maitri.routers import devices, health, sensors, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Maitri Backend", lifespan=lifespan)

app.include_router(health.router)
app.include_router(devices.router)
app.include_router(sensors.router)
app.include_router(websocket.router)


@app.get("/")
def root():
    return {"service": "maitri", "status": "running"}



