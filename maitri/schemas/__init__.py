"""Maitri Schemas Package."""

from maitri.schemas.device import DeviceBase, DeviceCreate, DeviceResponse
from maitri.schemas.sensor_reading import (
    SensorIngestRequest,
    SensorReadingBase,
    SensorReadingCreate,
    SensorReadingResponse,
)
from maitri.schemas.station import (
    SensorBase,
    SensorCreate,
    SensorResponse,
    StationBase,
    StationCreate,
    StationDetailResponse,
    StationResponse,
)

__all__ = [
    "DeviceBase",
    "DeviceCreate",
    "DeviceResponse",
    "SensorIngestRequest",
    "SensorReadingBase",
    "SensorReadingCreate",
    "SensorReadingResponse",
    "StationBase",
    "StationCreate",
    "StationResponse",
    "StationDetailResponse",
    "SensorBase",
    "SensorCreate",
    "SensorResponse",
]
