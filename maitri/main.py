from fastapi import FastAPI

from maitri.routers import devices, health, sensors

app = FastAPI(title="Maitri Backend")

app.include_router(health.router)
app.include_router(devices.router)
app.include_router(sensors.router)


@app.get("/")
def root():
    return {"service": "maitri", "status": "running"}

