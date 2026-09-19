"""WebSocket Connection and Broadcast Manager."""

import asyncio
from datetime import datetime, timezone
from typing import Any
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, message: dict):
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

    async def broadcast_telemetry(
        self,
        station_id: str | int,
        sensor_id: str,
        sensor_type: str,
        value: float,
        unit: str | None = None,
        timestamp: str | None = None,
        quality: str | None = "GOOD",
    ):
        """Broadcasts real-time telemetry with explicit station_id."""
        ts = timestamp or datetime.now(timezone.utc).isoformat()
        st_id = str(station_id)
        payload = {
            "type": "sensor_reading",
            "station_id": st_id,
            "sensor_id": sensor_id,
            "sensor_type": sensor_type,
            "value": value,
            "unit": unit,
            "quality": quality,
            "timestamp": ts,
            # Backwards compatibility fields for existing UI hooks
            "data": {
                "device_id": sensor_id,
                "metric": sensor_type,
                "value": value,
                "unit": unit,
            },
        }
        await self.broadcast_json(payload)

    def broadcast_telemetry_sync(self, **kwargs: Any):
        """Safe non-blocking broadcast callable from synchronous service contexts."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.broadcast_telemetry(**kwargs))
        except RuntimeError:
            pass


manager = ConnectionManager()
