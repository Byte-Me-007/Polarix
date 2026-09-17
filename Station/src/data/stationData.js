// Demo data — replace with backend API/WebSocket telemetry during integration.

/**
 * Configuration-driven Antarctic Research Stations (MAITRI & BHARATI)
 * Digital Platform for Efficient Remote Management of Indian Antarctic Research Stations (SIH 2026)
 */

export const STATIONS = {
  MAITRI: {
    stationId: "MAITRI",
    shortCode: "MTR",
    displayName: "Maitri Research Station",
    code: "MTR-IND",
    tagline: "Remote Station Monitoring & Decision Support",
    region: "Schirmacher Oasis, Queen Maud Land",
    coordinates: "70°45′58″ S, 11°43′56″ E",
    altitude: "117 m a.s.l.",
    elevation: "117 m a.s.l.",
    established: "1989",
    expedition: "45th Indian Scientific Expedition to Antarctica",
    personnelOnsite: 24,
    status: "OPERATIONAL",
    connection: "ONLINE",
    timeZoneOffsetHours: 1, // UTC+1 local solar time

    // Readiness configuration
    readiness: {
      score: 94,
      status: "HEALTHY",
      categories: [
        { name: "ENVIRONMENT", score: 96, status: "NOMINAL", icon: "CloudSnow" },
        { name: "ENERGY", score: 91, status: "OPTIMAL", icon: "Zap" },
        { name: "STRUCTURE", score: 97, status: "STABLE", icon: "Shield" },
        { name: "CONNECTIVITY", score: 94, status: "ONLINE", icon: "Radio" },
        { name: "ALERT LOAD", score: 89, status: "LOW_RISK", icon: "AlertTriangle" }
      ]
    },

    // Power Subsystem configuration
    power: {
      currentPower: "84.3 kW",
      loadPercentage: 68,
      solarGeneration: "42.8 kW",
      windGeneration: "18.4 kW",
      dieselGeneration: "23.1 kW",
      totalGeneration: "84.3 kW",
      peakLoad: "89.2 kW",
      sparklinePoints: "0,28 15,24 30,26 45,18 60,14 75,19 90,12 105,16 120,8 135,11 150,6"
    },

    // Battery Subsystem configuration
    battery: {
      percentage: 78,
      state: "CHARGING",
      voltage: "418.2 V",
      current: "+38.4 A",
      remainingHours: "38.5 hrs",
      cycles: 1420,
      health: "98.2%"
    },

    // Fuel Reserve configuration
    fuel: {
      currentLevel: 64,
      totalLiters: 53400,
      capacityLiters: 83400,
      dailyBurnRate: 480,
      remainingDays: 18.4,
      reserveStatus: "SECURE"
    },

    // Satellite & Communications configuration
    satellite: {
      status: "ONLINE",
      satellite: "GSAT-14 / Inmarsat-C",
      signalQuality: 96,
      latency: "42 ms",
      uplinkBandwidth: "12.4 Mbps",
      downlinkBandwidth: "28.6 Mbps",
      packetLoss: "0.02%"
    },

    // Environmental Telemetry baseline
    environmentalTelemetry: {
      temperature: -18.4,
      temperatureUnit: "°C",
      feelsLike: -28.1,
      pressure: 986.2,
      pressureUnit: "hPa",
      windSpeed: 42.5,
      windSpeedUnit: "km/h",
      windDirection: "SSE (158°)",
      humidity: 58,
      humidityUnit: "%",
      solarRadiation: 420,
      solarRadiationUnit: "W/m²",
      visibility: "24 km"
    },

    // Placeholder configuration for future 3D Digital Twin (Three.js)
    digitalTwin: {
      model: "/models/maitri_station.gltf",
      zones: [
        { id: "Z-01", name: "Main Living Module", status: "NOMINAL", temp: 21.2 },
        { id: "Z-02", name: "Science Laboratories", status: "NOMINAL", temp: 19.8 },
        { id: "Z-03", name: "Generator & Power Substation", status: "WARNING", temp: 24.5 },
        { id: "Z-04", name: "Storage & Life Support", status: "NOMINAL", temp: 16.0 }
      ],
      sensors: []
    },

    // Placeholder configuration for IoT sensor array topology
    sensors: [
      { id: "SN-MTR-01", name: "Anemometer Mast Alpha", type: "WIND_SPEED", unit: "km/h", x: 12.4, y: 8.5, z: 0.0, status: "ACTIVE" },
      { id: "SN-MTR-02", name: "External RTD Thermal Probe 1", type: "TEMPERATURE", unit: "°C", x: 5.2, y: 3.1, z: 1.2, status: "ACTIVE" },
      { id: "SN-MTR-03", name: "DG-2 Vibration Accelerometer", type: "VIBRATION", unit: "mm/s", x: -8.0, y: 14.2, z: -0.5, status: "WARNING" },
      { id: "SN-MTR-04", name: "Solar Array Pyranometer", type: "IRRADIANCE", unit: "W/m²", x: 18.0, y: -4.5, z: 2.0, status: "ACTIVE" }
    ]
  },

  BHARATI: {
    stationId: "BHARATI",
    shortCode: "BHR",
    displayName: "Bharati Research Station",
    code: "BHR-IND",
    tagline: "Remote Station Monitoring & Decision Support",
    region: "Larsemann Hills, East Antarctica",
    coordinates: "69°24′29″ S, 76°11′14″ E",
    altitude: "35 m a.s.l.",
    elevation: "35 m a.s.l.",
    established: "2012",
    expedition: "45th Indian Scientific Expedition to Antarctica",
    personnelOnsite: 19,
    status: "OPERATIONAL",
    connection: "ONLINE",
    timeZoneOffsetHours: 5, // UTC+5 local expedition time

    // Readiness configuration
    readiness: {
      score: 97,
      status: "OPTIMAL",
      categories: [
        { name: "ENVIRONMENT", score: 98, status: "NOMINAL", icon: "CloudSnow" },
        { name: "ENERGY", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "STRUCTURE", score: 99, status: "STABLE", icon: "Shield" },
        { name: "CONNECTIVITY", score: 97, status: "ONLINE", icon: "Radio" },
        { name: "ALERT LOAD", score: 95, status: "OPTIMAL", icon: "AlertTriangle" }
      ]
    },

    // Power Subsystem configuration
    power: {
      currentPower: "92.6 kW",
      loadPercentage: 54,
      solarGeneration: "54.2 kW",
      windGeneration: "22.8 kW",
      dieselGeneration: "15.6 kW",
      totalGeneration: "92.6 kW",
      peakLoad: "96.4 kW",
      sparklinePoints: "0,20 15,18 30,22 45,14 60,10 75,16 90,8 105,12 120,5 135,9 150,4"
    },

    // Battery Subsystem configuration
    battery: {
      percentage: 89,
      state: "FLOAT",
      voltage: "421.4 V",
      current: "+14.2 A",
      remainingHours: "52.0 hrs",
      cycles: 884,
      health: "99.4%"
    },

    // Fuel Reserve configuration
    fuel: {
      currentLevel: 84,
      totalLiters: 88200,
      capacityLiters: 105000,
      dailyBurnRate: 510,
      remainingDays: 164.0,
      reserveStatus: "SECURE"
    },

    // Satellite & Communications configuration
    satellite: {
      status: "ONLINE",
      satellite: "GSAT-30 / Starlink Gateway",
      signalQuality: 98,
      latency: "28 ms",
      uplinkBandwidth: "18.2 Mbps",
      downlinkBandwidth: "45.0 Mbps",
      packetLoss: "0.01%"
    },

    // Environmental Telemetry baseline
    environmentalTelemetry: {
      temperature: -12.6,
      temperatureUnit: "°C",
      feelsLike: -21.4,
      pressure: 994.5,
      pressureUnit: "hPa",
      windSpeed: 26.4,
      windSpeedUnit: "km/h",
      windDirection: "ENE (065°)",
      humidity: 64,
      humidityUnit: "%",
      solarRadiation: 530,
      solarRadiationUnit: "W/m²",
      visibility: "35 km"
    },

    // Placeholder configuration for future 3D Digital Twin (Three.js)
    digitalTwin: {
      model: "/models/bharati_station.gltf",
      zones: [
        { id: "Z-B01", name: "Integrated Habitats Module", status: "NOMINAL", temp: 22.0 },
        { id: "Z-B02", name: "Remote Sensing Laboratory", status: "NOMINAL", temp: 20.5 },
        { id: "Z-B03", name: "Clean Microgrid Plant", status: "NOMINAL", temp: 21.0 }
      ],
      sensors: []
    },

    // Placeholder configuration for IoT sensor array topology
    sensors: [
      { id: "SN-BHR-01", name: "Larsemann Anemometer Mast", type: "WIND_SPEED", unit: "km/h", x: 10.0, y: 12.0, z: 0.0, status: "ACTIVE" },
      { id: "SN-BHR-02", name: "Optical Surface Temperature Sensor", type: "TEMPERATURE", unit: "°C", x: 4.0, y: 2.0, z: 1.0, status: "ACTIVE" },
      { id: "SN-BHR-03", name: "Satellite Radome Feed Monitor", type: "RF_LEVEL", unit: "dBm", x: 0.0, y: 0.0, z: 6.5, status: "ACTIVE" }
    ]
  }
};

// Aliases for compatibility
export const BASE_TELEMETRY = {
  MAITRI: {
    healthScore: STATIONS.MAITRI.readiness.score,
    healthStatus: STATIONS.MAITRI.readiness.status,
    healthCategories: STATIONS.MAITRI.readiness.categories,
    power: STATIONS.MAITRI.power,
    battery: STATIONS.MAITRI.battery,
    fuel: STATIONS.MAITRI.fuel,
    connectivity: STATIONS.MAITRI.satellite,
    satellite: STATIONS.MAITRI.satellite,
    environment: STATIONS.MAITRI.environmentalTelemetry,
    environmentalTelemetry: STATIONS.MAITRI.environmentalTelemetry
  },
  BHARATI: {
    healthScore: STATIONS.BHARATI.readiness.score,
    healthStatus: STATIONS.BHARATI.readiness.status,
    healthCategories: STATIONS.BHARATI.readiness.categories,
    power: STATIONS.BHARATI.power,
    battery: STATIONS.BHARATI.battery,
    fuel: STATIONS.BHARATI.fuel,
    connectivity: STATIONS.BHARATI.satellite,
    satellite: STATIONS.BHARATI.satellite,
    environment: STATIONS.BHARATI.environmentalTelemetry,
    environmentalTelemetry: STATIONS.BHARATI.environmentalTelemetry
  }
};

export const INITIAL_ALERTS = [
  // MAITRI Alerts
  {
    id: "ALT-MTR-01",
    station: "MAITRI",
    severity: "CRITICAL",
    title: "Generator vibration anomaly",
    message: "DG Unit #2 harmonic vibration exceeds 4.8 mm/s threshold on primary rotor bearing.",
    subsystem: "ENERGY",
    timestamp: "12m ago",
    acknowledged: false
  },
  {
    id: "ALT-MTR-02",
    station: "MAITRI",
    severity: "WARNING",
    title: "High wind speed alert",
    message: "Anemometer Mast Alpha recorded sustained gusts reaching 68 km/h. Wind turbine pitch dampening auto-engaged.",
    subsystem: "ENVIRONMENT",
    timestamp: "38m ago",
    acknowledged: false
  },
  {
    id: "ALT-MTR-03",
    station: "MAITRI",
    severity: "WARNING",
    title: "Battery discharge rate elevated",
    message: "Substation Block 3 reporting momentary discharge current jump of 18A due to HVAC zone 2 defrost cycle.",
    subsystem: "BATTERY",
    timestamp: "1h 14m ago",
    acknowledged: true
  },
  {
    id: "ALT-MTR-04",
    station: "MAITRI",
    severity: "INFO",
    title: "Scheduled GSAT telemetry sync completed",
    message: "64 telemetry packets transmitted to NCPOR Goa mission operations ground terminal.",
    subsystem: "CONNECTIVITY",
    timestamp: "2h 05m ago",
    acknowledged: true
  },

  // BHARATI Alerts
  {
    id: "ALT-BHR-01",
    station: "BHARATI",
    severity: "INFO",
    title: "Fuel transfer pump cycle completed",
    message: "Automated fuel replenishment from Bulk Tank B to Day Tank completed nominally (1,200 L).",
    subsystem: "LOGISTICS",
    timestamp: "45m ago",
    acknowledged: true
  },
  {
    id: "ALT-BHR-02",
    station: "BHARATI",
    severity: "INFO",
    title: "Larsemann optical radome calibrated",
    message: "Starlink gateway RF signal-to-noise ratio tested at 24 dB. Uplink channel cleared.",
    subsystem: "CONNECTIVITY",
    timestamp: "2h 10m ago",
    acknowledged: true
  }
];

// 24-hour historical environmental readings for ECharts trend visualizer
export const generate24HourTelemetry = (baseTemp = -18.4, baseWind = 42.5) => {
  const hours = [
    "00:00", "02:00", "04:00", "06:00", "08:00", "10:00", 
    "12:00", "14:00", "16:00", "18:00", "20:00", "22:00", "Now"
  ];

  const temps = hours.map((_, i) => {
    // slight diurnal cycle
    const cycle = Math.sin((i / 12) * Math.PI) * 4.2;
    return Number((baseTemp + cycle - 2.5 + (i * 0.15)).toFixed(1));
  });

  const winds = hours.map((_, i) => {
    const gust = (Math.cos(i) * 8);
    return Math.max(5, Number((baseWind + gust).toFixed(1)));
  });

  const pressures = hours.map((_, i) => {
    return Number((982 + (i * 0.4) + Math.sin(i * 0.8) * 3).toFixed(1));
  });

  const humidities = hours.map((_, i) => {
    return Math.min(85, Math.max(30, Math.round(56 + Math.sin(i * 0.5) * 8)));
  });

  return { hours, temps, winds, pressures, humidities };
};

// Scenario presets for DEMO MODE
export const DEMO_SCENARIOS = {
  NORMAL: {
    label: "NORMAL",
    badge: "STANDARD OPERATIONS",
    description: "Nominal operational telemetry across all Antarctic station life-support subsystems.",
    patch: {},
    addedAlerts: []
  },
  STORM: {
    label: "STORM",
    badge: "BLIZZARD CODE RED",
    description: "Catastrophic Antarctic blizzard detected. 118 km/h wind gusts, rapid barometric drop.",
    patch: {
      healthScore: 74,
      healthStatus: "DEGRADED",
      environment: {
        temperature: -34.8,
        windSpeed: 118.4,
        pressure: 958.0,
        humidity: 88
      },
      environmentalTelemetry: {
        temperature: -34.8,
        windSpeed: 118.4,
        pressure: 958.0,
        humidity: 88
      },
      power: {
        currentPower: "89.2 kW",
        solarGeneration: "0.0 kW",
        windGeneration: "62.5 kW",
        batteryPercentage: 84
      },
      battery: {
        percentage: 84,
        state: "DISCHARGING",
        remainingHours: "19.2 hrs"
      },
      healthCategories: [
        { name: "ENVIRONMENT", score: 58, status: "CRITICAL", icon: "CloudSnow" },
        { name: "ENERGY", score: 82, status: "WARNING", icon: "Zap" },
        { name: "STRUCTURE", score: 84, status: "WARNING", icon: "Shield" },
        { name: "CONNECTIVITY", score: 78, status: "DEGRADED", icon: "Radio" },
        { name: "ALERT LOAD", score: 62, status: "HIGH_RISK", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-01",
        station: "ALL",
        severity: "CRITICAL",
        title: "Severe Blizzard Warning — 118 km/h gusts",
        message: "External shelter lockdown protocol active. Optical visibility < 50m. Solar array auto-stowed.",
        subsystem: "ENVIRONMENT",
        timestamp: "Just now",
        acknowledged: false
      }
    ]
  },
  SENSOR_FAILURE: {
    label: "SENSOR FAILURE",
    badge: "TELEMETRY FAULT",
    description: "Multiplexer communication dropout on East Mast Met Sensor Cluster.",
    patch: {
      healthScore: 82,
      healthStatus: "MONITORING",
      environment: {
        humidity: 0
      },
      environmentalTelemetry: {
        humidity: 0
      },
      healthCategories: [
        { name: "ENVIRONMENT", score: 70, status: "WARNING", icon: "CloudSnow" },
        { name: "ENERGY", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "STRUCTURE", score: 98, status: "STABLE", icon: "Shield" },
        { name: "CONNECTIVITY", score: 92, status: "ONLINE", icon: "Radio" },
        { name: "ALERT LOAD", score: 76, status: "WARNING", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-02",
        station: "ALL",
        severity: "WARNING",
        title: "Telemetry Array Bus Offline",
        message: "RS-485 bus heartbeat lost on Humidity Sensor Node #4. Fallback estimation active.",
        subsystem: "SENSORS",
        timestamp: "Just now",
        acknowledged: false
      }
    ]
  },
  POWER_CRISIS: {
    label: "POWER CRISIS",
    badge: "ENERGY EMERGENCY",
    description: "DG #1 and DG #2 trip; battery bank sustaining critical life support under severe load.",
    patch: {
      healthScore: 48,
      healthStatus: "CRITICAL",
      power: {
        currentPower: "44.0 kW",
        solarGeneration: "2.1 kW",
        windGeneration: "12.0 kW",
        dieselGeneration: "0.0 kW",
        batteryPercentage: 42
      },
      battery: {
        percentage: 42,
        state: "CRITICAL DISCHARGE",
        remainingHours: "7.4 hrs"
      },
      healthCategories: [
        { name: "ENVIRONMENT", score: 88, status: "NOMINAL", icon: "CloudSnow" },
        { name: "ENERGY", score: 38, status: "CRITICAL", icon: "Zap" },
        { name: "STRUCTURE", score: 94, status: "STABLE", icon: "Shield" },
        { name: "CONNECTIVITY", score: 80, status: "WARNING", icon: "Radio" },
        { name: "ALERT LOAD", score: 32, status: "EMERGENCY", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-03",
        station: "ALL",
        severity: "CRITICAL",
        title: "Microgrid Generator Trip & Battery Drain",
        message: "Auxiliary power active. Non-essential scientific heating disabled to conserve battery bank.",
        subsystem: "ENERGY",
        timestamp: "Just now",
        acknowledged: false
      }
    ]
  },
  SATELLITE_OUTAGE: {
    label: "SATELLITE OUTAGE",
    badge: "COMMS BLACKOUT",
    description: "Primary satellite tracking dish misalignment due to geomagnetic solar storm.",
    patch: {
      healthScore: 68,
      healthStatus: "DEGRADED",
      satellite: {
        status: "OFFLINE",
        satellite: "DISCONNECTED",
        signalQuality: 0,
        latency: "FAIL",
        packetLoss: "100%"
      },
      connectivity: {
        status: "OFFLINE",
        satellite: "DISCONNECTED",
        signalQuality: 0,
        latency: "FAIL",
        packetLoss: "100%"
      },
      healthCategories: [
        { name: "ENVIRONMENT", score: 92, status: "NOMINAL", icon: "CloudSnow" },
        { name: "ENERGY", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "STRUCTURE", score: 98, status: "STABLE", icon: "Shield" },
        { name: "CONNECTIVITY", score: 22, status: "OFFLINE", icon: "Radio" },
        { name: "ALERT LOAD", score: 60, status: "WARNING", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-04",
        station: "ALL",
        severity: "CRITICAL",
        title: "Satellite Uplink Lost — Comms Blackout",
        message: "Telemetry buffering to local solid-state logger. Auto-switching to emergency HF radio packet burst.",
        subsystem: "CONNECTIVITY",
        timestamp: "Just now",
        acknowledged: false
      }
    ]
  },
  RECOVERY: {
    label: "RECOVERY",
    badge: "RESTORING NOMINAL",
    description: "System recovery routines executed. Subsystems re-engaging to nominal baseline.",
    patch: {},
    addedAlerts: [
      {
        id: "ALT-SCN-REC",
        station: "ALL",
        severity: "INFO",
        title: "Diagnostic Self-Test Completed",
        message: "Microgrid and satellite uplink verified nominal on active station bus.",
        subsystem: "SYSTEM",
        timestamp: "Just now",
        acknowledged: true
      }
    ]
  }
};
