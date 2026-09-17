from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Maitri Backend"
    environment: str = "development"
    database_url: str = "sqlite:///./maitri.db"


settings = Settings()
