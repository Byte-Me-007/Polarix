from datetime import datetime
import json
from typing import Any
from pydantic import BaseModel, ConfigDict, field_validator


class CommandCreate(BaseModel):
    command_id: str | None = None
    station_id: int | None = None
    station_code: str | None = None
    command_type: str  # START_SCENARIO, STOP_SCENARIO, SET_NETWORK_OFFLINE, SET_NETWORK_ONLINE, REQUEST_SYNC, ACKNOWLEDGE_ALERT, RESOLVE_ALERT
    payload: dict[str, Any] | str | None = None


class CommandResponse(BaseModel):
    id: int
    command_id: str
    station_id: int | None = None
    command_type: str
    status: str  # PENDING, EXECUTED, FAILED
    payload: dict[str, Any] | str | None = None
    result_message: str | None = None
    created_at: datetime
    executed_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("payload", mode="before")
    @classmethod
    def parse_payload(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except Exception:
                return v
        return v
