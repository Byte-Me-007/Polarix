from fastapi import FastAPI

from bharati.routers import health

app = FastAPI(title="Bharati Backend")

app.include_router(health.router)


@app.get("/")
def root():
    return {"service": "bharati", "status": "running"}
