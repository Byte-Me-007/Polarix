"""Maitri Schemas Package."""

from maitri.schemas.device import DeviceBase, DeviceCreate, DeviceResponse
from maitri.schemas.sensor_reading import (
    SensorReadingBase,
    SensorReadingCreate,
    SensorReadingResponse,
)

__all__ = [
    "DeviceBase",
    "DeviceCreate",
    "DeviceResponse",
    "SensorReadingBase",
    "SensorReadingCreate",
    "SensorReadingResponse",
]
