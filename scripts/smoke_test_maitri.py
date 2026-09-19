import json
import sys
import httpx
from websockets.sync.client import connect as ws_connect

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000/ws/sensor-readings"


def run_smoke_test():
    print(f"Starting Maitri Smoke Test against {BASE_URL} and {WS_URL}...\n")
    with httpx.Client(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Health check
        print("1. Checking GET /health ...")
        try:
            res_health = client.get("/health")
        except Exception as exc:
            print(f"[FAIL] Could not connect to {BASE_URL}: {exc}")
            sys.exit(1)

        if res_health.status_code != 200:
            print(f"[FAIL] /health returned status {res_health.status_code}: {res_health.text}")
            sys.exit(1)
        print(f"[OK] Health check passed: {res_health.json()}\n")

        # 2. Register smoke test device
        print("2. Registering smoke test device via POST /devices/ ...")
        device_payload = {
            "device_id": "smoke-device-001",
            "name": "Smoke Test Device",
            "location": "local",
            "status": "active",
        }
        res_device = client.post("/devices/", json=device_payload)
        if res_device.status_code in (200, 201):
            print(f"[OK] Device created: {res_device.json()}\n")
        elif res_device.status_code == 400:
            print(f"[INFO] Device 'smoke-device-001' already exists (status 400), continuing...\n")
        else:
            print(f"[FAIL] POST /devices/ failed with status {res_device.status_code}: {res_device.text}")
            sys.exit(1)

        # 3. Ingest sensor reading
        print("3. Ingesting sensor reading via POST /sensor-readings/ingest ...")
        payload_data = {
            "device_id": "smoke-device-001",
            "metric": "temperature",
            "value": 24.5,
            "unit": "celsius",
        }
        ingest_payload = {"payload": json.dumps(payload_data)}
        res_ingest = client.post("/sensor-readings/ingest", json=ingest_payload)
        if res_ingest.status_code != 200:
            print(f"[FAIL] Ingestion failed with status {res_ingest.status_code}: {res_ingest.text}")
            sys.exit(1)
        print(f"[OK] Reading ingested successfully: {res_ingest.json()}\n")

        # 4. Fetch readings for device
        print("4. Querying readings via GET /sensor-readings/device/smoke-device-001 ...")
        res_get_readings = client.get("/sensor-readings/device/smoke-device-001")
        if res_get_readings.status_code != 200:
            print(f"[FAIL] GET readings failed with status {res_get_readings.status_code}: {res_get_readings.text}")
            sys.exit(1)

        readings = res_get_readings.json()
        print(f"[OK] Retrieved {len(readings)} reading(s) for smoke-device-001.")
        print(f"Latest reading: {readings[-1] if readings else 'None'}\n")

    # 5. WebSocket verification
    print(f"5. Verifying WebSocket connection at {WS_URL} ...")
    try:
        with ws_connect(WS_URL, open_timeout=10.0, close_timeout=10.0) as ws:
            ws.send("ping")
            raw_response = ws.recv()
            ws_response = json.loads(raw_response) if isinstance(raw_response, str) else raw_response
            if ws_response.get("type") != "ack" or ws_response.get("message") != "connected":
                print(f"[FAIL] Unexpected WebSocket response: {ws_response}")
                sys.exit(1)
            print(f"[OK] WebSocket response acknowledged: {ws_response}\n")
    except Exception as exc:
        print(f"[FAIL] WebSocket test failed: {exc}")
        sys.exit(1)

    print("ALL SMOKE TESTS (HTTP + WEBSOCKET) PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_smoke_test()
