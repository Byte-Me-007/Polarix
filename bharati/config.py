import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    app_name: str = Field(
        default_factory=lambda: os.getenv(
            "BHARATI_APP_NAME", os.getenv("APP_NAME", "Bharati Backend")
        )
    )
    environment: str = Field(
        default_factory=lambda: os.getenv(
            "BHARATI_ENVIRONMENT", os.getenv("ENVIRONMENT", "development")
        )
    )
    database_url: str = Field(
        default_factory=lambda: os.getenv(
            "BHARATI_DATABASE_URL",
            os.getenv("DATABASE_URL", "sqlite:///./bharati.db"),
        )
    )


settings = Settings()
