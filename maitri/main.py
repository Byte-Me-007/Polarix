from fastapi import FastAPI

from maitri.routers import health

app = FastAPI(title="Maitri Backend")

app.include_router(health.router)


@app.get("/")
def root():
    return {"service": "maitri", "status": "running"}
