import os
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()


class Settings(BaseModel):
    app_name: str = Field(
        default_factory=lambda: os.getenv("APP_NAME", "Maitri Backend")
    )
    environment: str = Field(
        default_factory=lambda: os.getenv("ENVIRONMENT", "development")
    )
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./maitri.db")
    )
    mqtt_broker_host: str = Field(
        default_factory=lambda: os.getenv("MQTT_BROKER_HOST", "localhost")
    )
    mqtt_broker_port: int = Field(
        default_factory=lambda: int(os.getenv("MQTT_BROKER_PORT", "1883"))
    )
    mqtt_topic_prefix: str = Field(
        default_factory=lambda: os.getenv("MQTT_TOPIC_PREFIX", "antarctic")
    )


settings = Settings()

