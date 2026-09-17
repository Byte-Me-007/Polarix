// Antarctic Research Stations Configuration and Baseline Telemetry Data

export const STATIONS = {
  MAITRI: {
    id: "MTR",
    name: "MAITRI",
    fullName: "Maitri Antarctic Research Station",
    code: "MTR-IND",
    tagline: "Remote Station Monitoring & Decision Support",
    coordinates: "70°45′58″ S, 11°43′56″ E",
    region: "Schirmacher Oasis, Queen Maud Land",
    elevation: "117 m a.s.l.",
    established: "1989",
    expedition: "45th Indian Scientific Expedition to Antarctica",
    personnelOnsite: 24,
    status: "OPERATIONAL",
    connection: "ONLINE"
  },
  BHARATI: {
    id: "BHR",
    name: "BHARATI",
    fullName: "Bharati Antarctic Research Station",
    code: "BHR-IND",
    tagline: "Remote Station Monitoring & Decision Support",
    coordinates: "69°24′29″ S, 76°11′14″ E",
    region: "Larsemann Hills, East Antarctica",
    elevation: "35 m a.s.l.",
    established: "2012",
    expedition: "45th Indian Scientific Expedition to Antarctica",
    personnelOnsite: 19,
    status: "OPERATIONAL",
    connection: "ONLINE"
  }
};

export const BASE_TELEMETRY = {
  MAITRI: {
    healthScore: 94,
    healthStatus: "HEALTHY",
    healthCategories: [
      { name: "Environment", score: 92, status: "NOMINAL", icon: "CloudSnow" },
      { name: "Energy", score: 96, status: "OPTIMAL", icon: "Zap" },
      { name: "Structure", score: 98, status: "STABLE", icon: "Shield" },
      { name: "Connectivity", score: 95, status: "ONLINE", icon: "Radio" },
      { name: "Critical Alerts", score: 89, status: "LOW_RISK", icon: "AlertTriangle" }
    ],
    power: {
      currentPower: "76.4 kW",
      loadPercentage: 64,
      solarGeneration: "18.5 kW",
      windGeneration: "34.2 kW",
      dieselGeneration: "23.7 kW",
      batteryPercentage: 91,
      totalGeneration: "76.4 kW"
    },
    battery: {
      percentage: 91,
      state: "CHARGING",
      voltage: "418.2 V",
      current: "+44.1 A",
      remainingHours: "38.5 hrs",
      cycles: 1420,
      health: "98.2%"
    },
    fuel: {
      currentLevel: 82,
      totalLiters: 68400,
      capacityLiters: 83400,
      dailyBurnRate: 480,
      remainingDays: 142,
      reserveStatus: "SECURE"
    },
    connectivity: {
      status: "ONLINE",
      satellite: "GSAT-14 / Inmarsat-C",
      signalQuality: 96,
      latency: "318 ms",
      uplinkBandwidth: "12.4 Mbps",
      downlinkBandwidth: "28.6 Mbps",
      packetLoss: "0.02%"
    },
    environment: {
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
    }
  },
  BHARATI: {
    healthScore: 97,
    healthStatus: "OPTIMAL",
    healthCategories: [
      { name: "Environment", score: 95, status: "NOMINAL", icon: "CloudSnow" },
      { name: "Energy", score: 98, status: "OPTIMAL", icon: "Zap" },
      { name: "Structure", score: 99, status: "STABLE", icon: "Shield" },
      { name: "Connectivity", score: 96, status: "ONLINE", icon: "Radio" },
      { name: "Critical Alerts", score: 97, status: "OPTIMAL", icon: "AlertTriangle" }
    ],
    power: {
      currentPower: "88.2 kW",
      loadPercentage: 58,
      solarGeneration: "22.8 kW",
      windGeneration: "41.6 kW",
      dieselGeneration: "23.8 kW",
      batteryPercentage: 94,
      totalGeneration: "88.2 kW"
    },
    battery: {
      percentage: 94,
      state: "FLOAT",
      voltage: "421.0 V",
      current: "+12.4 A",
      remainingHours: "44.2 hrs",
      cycles: 884,
      health: "99.4%"
    },
    fuel: {
      currentLevel: 88,
      totalLiters: 92400,
      capacityLiters: 105000,
      dailyBurnRate: 510,
      remainingDays: 181,
      reserveStatus: "SECURE"
    },
    connectivity: {
      status: "ONLINE",
      satellite: "GSAT-30 / Starlink Gateway",
      signalQuality: 98,
      latency: "245 ms",
      uplinkBandwidth: "18.2 Mbps",
      downlinkBandwidth: "45.0 Mbps",
      packetLoss: "0.01%"
    },
    environment: {
      temperature: -14.2,
      temperatureUnit: "°C",
      feelsLike: -22.5,
      pressure: 994.0,
      pressureUnit: "hPa",
      windSpeed: 28.0,
      windSpeedUnit: "km/h",
      windDirection: "ENE (065°)",
      humidity: 62,
      humidityUnit: "%",
      solarRadiation: 510,
      solarRadiationUnit: "W/m²",
      visibility: "32 km"
    }
  }
};

export const INITIAL_ALERTS = [
  {
    id: "ALT-01",
    station: "MAITRI",
    severity: "CRITICAL",
    title: "Generator vibration anomaly",
    message: "DG Unit #2 harmonic vibration exceeds 4.8 mm/s threshold on primary rotor bearing.",
    subsystem: "ENERGY",
    timestamp: "12m ago",
    acknowledged: false
  },
  {
    id: "ALT-02",
    station: "MAITRI",
    severity: "WARNING",
    title: "High wind speed alert",
    message: "Anemometer Mast 1 recorded sustained gusts reaching 68 km/h. Wind turbine pitch dampening auto-engaged.",
    subsystem: "ENVIRONMENT",
    timestamp: "38m ago",
    acknowledged: false
  },
  {
    id: "ALT-03",
    station: "MAITRI",
    severity: "WARNING",
    title: "Battery discharge rate elevated",
    message: "Substation Block 3 reporting momentary discharge current jump of 18A due to HVAC zone 2 defrost cycle.",
    subsystem: "BATTERY",
    timestamp: "1h 14m ago",
    acknowledged: true
  },
  {
    id: "ALT-04",
    station: "MAITRI",
    severity: "INFO",
    title: "Scheduled GSAT telemetry sync completed",
    message: "64 telemetry packets transmitted to NCPOR Goa mission operations ground terminal.",
    subsystem: "CONNECTIVITY",
    timestamp: "2h 05m ago",
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
    const gust = (Math.cos(i) * 12);
    return Math.max(10, Number((baseWind + gust).toFixed(1)));
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
    patch: {
      healthScore: 94,
      healthStatus: "HEALTHY",
      environment: {
        temperature: -18.4,
        windSpeed: 42.5,
        pressure: 986.2,
        humidity: 58
      },
      power: {
        currentPower: "76.4 kW",
        solarGeneration: "18.5 kW",
        windGeneration: "34.2 kW",
        batteryPercentage: 91
      },
      battery: {
        percentage: 91,
        state: "CHARGING",
        remainingHours: "38.5 hrs"
      },
      connectivity: {
        status: "ONLINE",
        signalQuality: 96,
        latency: "318 ms"
      },
      healthCategories: [
        { name: "Environment", score: 92, status: "NOMINAL", icon: "CloudSnow" },
        { name: "Energy", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "Structure", score: 98, status: "STABLE", icon: "Shield" },
        { name: "Connectivity", score: 95, status: "ONLINE", icon: "Radio" },
        { name: "Critical Alerts", score: 89, status: "LOW_RISK", icon: "AlertTriangle" }
      ]
    },
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
        { name: "Environment", score: 58, status: "CRITICAL", icon: "CloudSnow" },
        { name: "Energy", score: 82, status: "WARNING", icon: "Zap" },
        { name: "Structure", score: 84, status: "WARNING", icon: "Shield" },
        { name: "Connectivity", score: 78, status: "DEGRADED", icon: "Radio" },
        { name: "Critical Alerts", score: 62, status: "HIGH_RISK", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-01",
        station: "MAITRI",
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
        temperature: -18.4,
        windSpeed: 42.5,
        pressure: 986.2,
        humidity: 0 // degraded
      },
      healthCategories: [
        { name: "Environment", score: 70, status: "WARNING", icon: "CloudSnow" },
        { name: "Energy", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "Structure", score: 98, status: "STABLE", icon: "Shield" },
        { name: "Connectivity", score: 92, status: "ONLINE", icon: "Radio" },
        { name: "Critical Alerts", score: 76, status: "WARNING", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-02",
        station: "MAITRI",
        severity: "WARNING",
        title: "East Mast Telemetry Array Offline",
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
        { name: "Environment", score: 88, status: "NOMINAL", icon: "CloudSnow" },
        { name: "Energy", score: 38, status: "CRITICAL", icon: "Zap" },
        { name: "Structure", score: 94, status: "STABLE", icon: "Shield" },
        { name: "Connectivity", score: 80, status: "WARNING", icon: "Radio" },
        { name: "Critical Alerts", score: 32, status: "EMERGENCY", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-03",
        station: "MAITRI",
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
    description: "Primary Ku-Band satellite tracking dish misalignment due to geomagnetic solar storm.",
    patch: {
      healthScore: 68,
      healthStatus: "DEGRADED",
      connectivity: {
        status: "OFFLINE",
        satellite: "GSAT-14 (DISCONNECTED)",
        signalQuality: 0,
        latency: "FAIL",
        packetLoss: "100%"
      },
      healthCategories: [
        { name: "Environment", score: 92, status: "NOMINAL", icon: "CloudSnow" },
        { name: "Energy", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "Structure", score: 98, status: "STABLE", icon: "Shield" },
        { name: "Connectivity", score: 22, status: "OFFLINE", icon: "Radio" },
        { name: "Critical Alerts", score: 60, status: "WARNING", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-04",
        station: "MAITRI",
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
    patch: {
      healthScore: 94,
      healthStatus: "HEALTHY",
      environment: {
        temperature: -18.4,
        windSpeed: 42.5,
        pressure: 986.2,
        humidity: 58
      },
      power: {
        currentPower: "76.4 kW",
        solarGeneration: "18.5 kW",
        windGeneration: "34.2 kW",
        dieselGeneration: "23.7 kW",
        batteryPercentage: 91
      },
      battery: {
        percentage: 91,
        state: "CHARGING",
        remainingHours: "38.5 hrs"
      },
      connectivity: {
        status: "ONLINE",
        satellite: "GSAT-14 / Inmarsat-C",
        signalQuality: 96,
        latency: "318 ms"
      },
      healthCategories: [
        { name: "Environment", score: 92, status: "NOMINAL", icon: "CloudSnow" },
        { name: "Energy", score: 96, status: "OPTIMAL", icon: "Zap" },
        { name: "Structure", score: 98, status: "STABLE", icon: "Shield" },
        { name: "Connectivity", score: 95, status: "ONLINE", icon: "Radio" },
        { name: "Critical Alerts", score: 89, status: "LOW_RISK", icon: "AlertTriangle" }
      ]
    },
    addedAlerts: [
      {
        id: "ALT-SCN-REC",
        station: "MAITRI",
        severity: "INFO",
        title: "Diagnostic Self-Test Completed",
        message: "Microgrid and satellite uplink restored to nominal operating parameters.",
        subsystem: "SYSTEM",
        timestamp: "Just now",
        acknowledged: true
      }
    ]
  }
};
