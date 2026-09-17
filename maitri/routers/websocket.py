from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from maitri.services.websocket_manager import manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/sensor-readings")
async def websocket_sensor_readings(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_json({"type": "ack", "message": "connected"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
