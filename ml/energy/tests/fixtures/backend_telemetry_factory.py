"""
Backend Telemetry Factory Fixture (Polarix SIH26060).

Generates deterministic, physically grounded canonical backend-style telemetry records
for integration and end-to-end streaming harness tests.
Guarantees:
- Output records contain ONLY canonical physical fields and optional sensor ML flags.
- Zero future target columns (no target_* or future_* fields).
- Zero ML-derived features (no rolling means, slopes, ratios, or sin/cos encodings).
- Deterministic across fixed seeds.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union

import numpy as np


class BackendTelemetryFactory:
    """Factory for generating realistic, canonical backend telemetry streams."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.RandomState(seed)

    def create_record(
        self,
        station_id: str = "MTR",
        timestamp: Optional[Union[str, datetime]] = None,
        power_demand_kw: Optional[float] = None,
        generator_output_kw: Optional[float] = None,
        battery_soc_percent: Optional[float] = None,
        include_optional_sensor_ml: bool = True,
        source: str = "SIMULATOR",
        data_quality: str = "GOOD",
    ) -> Dict[str, Any]:
        """Generate a single canonical backend telemetry record."""
        if timestamp is None:
            ts_dt = datetime(2026, 9, 18, 0, 0, 0, tzinfo=timezone.utc)
        elif isinstance(timestamp, str):
            clean_ts = timestamp.strip().replace("Z", "+00:00")
            ts_dt = datetime.fromisoformat(clean_ts).astimezone(timezone.utc)
        elif isinstance(timestamp, datetime):
            ts_dt = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=timezone.utc)
        else:
            raise TypeError(f"Invalid timestamp type: {type(timestamp)}")

        iso_ts = ts_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        is_brt = station_id == "BRT"

        # Base load profile
        base_demand = 60.0 if is_brt else 48.0
        hour = ts_dt.hour
        diurnal_factor = 1.0 + 0.20 * np.sin(2.0 * np.pi * (hour - 6) / 24.0)

        p_demand = (
            float(power_demand_kw)
            if power_demand_kw is not None
            else float(np.clip(base_demand * diurnal_factor + self.rng.normal(0.0, 2.5), 15.0, 140.0))
        )

        # Generator tracks demand + small charging reserve
        gen_out = (
            float(generator_output_kw)
            if generator_output_kw is not None
            else float(np.clip(p_demand + 4.0 + self.rng.uniform(0.0, 3.0), 15.0, 150.0))
        )

        soc = (
            float(battery_soc_percent)
            if battery_soc_percent is not None
            else float(np.clip(80.0 - 5.0 * np.sin(2.0 * np.pi * hour / 24.0) + self.rng.normal(0.0, 1.5), 20.0, 95.0))
        )

        # Net flow: if generator > demand, charging; else discharging
        net_diff = gen_out - p_demand
        if net_diff >= 0:
            b_chg = float(min(net_diff, 25.0))
            b_dis = 0.0
        else:
            b_chg = 0.0
            b_dis = float(min(-net_diff, 25.0))

        # Fuel consumption (BSFC quadratic model)
        a0 = 2.15 if is_brt else 1.85
        a1 = 0.242 if is_brt else 0.238
        a2 = 0.00012 if is_brt else 0.00015
        fuel = float(np.clip(a0 + a1 * gen_out + a2 * (gen_out**2) + self.rng.normal(0.0, 0.2), 3.0, 50.0))

        # Meteorological telemetry
        temp = float(np.clip(-22.0 + 8.0 * np.sin(2.0 * np.pi * (hour - 8) / 24.0) + self.rng.normal(0.0, 1.5), -50.0, 5.0))
        humidity = float(np.clip(60.0 + self.rng.normal(0.0, 5.0), 20.0, 95.0))
        pressure = float(np.clip(985.0 + self.rng.normal(0.0, 3.0), 930.0, 1030.0))
        wind = float(np.clip(8.0 + self.rng.exponential(4.0), 0.5, 55.0))

        record: Dict[str, Any] = {
            "timestamp": iso_ts,
            "station_id": station_id,
            "power_demand_kw": round(p_demand, 2),
            "generator_output_kw": round(gen_out, 2),
            "battery_soc_percent": round(soc, 2),
            "battery_charge_kw": round(b_chg, 2),
            "battery_discharge_kw": round(b_dis, 2),
            "fuel_consumption_l": round(fuel, 2),
            "temperature_c": round(temp, 2),
            "humidity_percent": round(humidity, 2),
            "pressure_hpa": round(pressure, 2),
            "wind_speed_mps": round(wind, 2),
        }

        if include_optional_sensor_ml:
            record["sensor_anomaly_score"] = round(float(np.clip(self.rng.gamma(1.5, 0.5), 0.1, 5.0)), 4)
            record["sensor_anomaly_status"] = "NORMAL"
            record["sensor_anomaly_type"] = "NORMAL"
            record["data_quality"] = data_quality
            record["source"] = source

        return record

    def create_stream(
        self,
        station_id: str = "MTR",
        start_time: Union[str, datetime] = "2026-09-18T00:00:00Z",
        num_hours: int = 24,
        step_hours: int = 1,
        include_optional_sensor_ml: bool = True,
        source: str = "SIMULATOR",
    ) -> List[Dict[str, Any]]:
        """Generate a consecutive hourly sequence of canonical telemetry records."""
        if isinstance(start_time, str):
            clean_ts = start_time.strip().replace("Z", "+00:00")
            curr_dt = datetime.fromisoformat(clean_ts).astimezone(timezone.utc)
        else:
            curr_dt = start_time if start_time.tzinfo else start_time.replace(tzinfo=timezone.utc)

        stream = []
        for _ in range(num_hours):
            rec = self.create_record(
                station_id=station_id,
                timestamp=curr_dt,
                include_optional_sensor_ml=include_optional_sensor_ml,
                source=source,
            )
            stream.append(rec)
            curr_dt += timedelta(hours=step_hours)

        return stream
