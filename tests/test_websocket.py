import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from maitri.database import Base, get_db
from maitri.main import app


@pytest.fixture
def client():
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_websocket_connection_and_ack(client):
    with client.websocket_connect("/ws/sensor-readings") as websocket:
        websocket.send_text("hello")
        data = websocket.receive_json()
        assert data["type"] == "ack"
        assert data["message"] == "connected"


def test_websocket_broadcast_on_ingest(client):
    with client.websocket_connect("/ws/sensor-readings") as websocket:
        payload_data = {
            "device_id": "ws-device-001",
            "metric": "temperature",
            "value": 22.4,
            "unit": "celsius",
        }
        res = client.post(
            "/sensor-readings/ingest",
            json={"payload": json.dumps(payload_data)},
        )
        assert res.status_code == 200

        msg = websocket.receive_json()
        assert msg["type"] == "sensor_reading"
        assert msg["data"]["device_id"] == "ws-device-001"
        assert msg["data"]["metric"] == "temperature"
        assert msg["data"]["value"] == 22.4
