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

    // 3D Digital Twin configuration with 6 required spatial zones arranged in modular connected layout
    digitalTwin: {
      model: "procedural-parametric",
      elevationStilts: true,
      zones: [
        { id: "Z-MTR-01", name: "MAIN BUILDING", code: "MAIN", position: [0, 1.6, 0], size: [11.5, 3.0, 7.0], shape: "box", color: "#e8e4dc", status: "NOMINAL", description: "Central living module, briefing facility, command hub, and life support" },
        { id: "Z-MTR-02", name: "ENERGY", code: "ENERGY", position: [0, 1.4, -7.2], size: [6.0, 2.5, 5.0], shape: "box", color: "#dfd9ce", status: "NOMINAL", description: "Microgrid power conditioning, battery storage banks, and solar inverters" },
        { id: "Z-MTR-03", name: "RESEARCH", code: "RESEARCH", position: [9.5, 1.4, 0], size: [5.5, 2.5, 5.5], shape: "box", color: "#dfd9ce", status: "NOMINAL", description: "Meteorological, atmospheric, and geomagnetic scientific research labs" },
        { id: "Z-MTR-04", name: "STORAGE", code: "STORAGE", position: [8.5, 1.2, -7.2], size: [6.0, 2.2, 4.8], shape: "box", color: "#d6cfc3", status: "NOMINAL", description: "Deep cold provisions, spares, logistics container modules, and supplies" },
        { id: "Z-MTR-05", name: "GENERATOR", code: "GENERATOR", position: [-8.5, 1.3, -7.2], size: [5.5, 2.3, 4.8], shape: "box", color: "#d9d0c2", status: "WARNING", description: "Auxiliary diesel generator units #1 & #2, fuel buffer, and exhaust plant" },
        { id: "Z-MTR-06", name: "COMMS", code: "COMMS", position: [0, 3.2, -13.5], size: [2.2, 4.5, 2.2], shape: "cylinder", color: "#b65a1f", status: "NOMINAL", description: "Primary Ku-Band satellite tracking dish, telemetry shelter, and antenna mast" }
      ],
      sensors: []
    },

    // Comprehensive sensor registry configuration mapped to 3D station zones
    sensors: [
      { id: "ENV-MTR-001", name: "Ambient Meteorological RTD", domain: "ENVIRONMENT", type: "TEMPERATURE", value: -18.4, unit: "°C", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:09 UTC", criticality: "HIGH", minValue: -50.0, maxValue: 10.0, x: 2.5, y: 3.1, z: 2.5 },
      { id: "ENV-MTR-002", name: "Anemometer Mast Alpha", domain: "ENVIRONMENT", type: "WIND_SPEED", value: 42.5, unit: "km/h", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:07 UTC", criticality: "HIGH", minValue: 0.0, maxValue: 160.0, x: 0.0, y: 6.8, z: -13.5 },
      { id: "ENV-MTR-003", name: "Barometric Pressure Transducer", domain: "ENVIRONMENT", type: "PRESSURE", value: 986.2, unit: "hPa", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:55 UTC", criticality: "MEDIUM", minValue: 920.0, maxValue: 1040.0, x: -2.5, y: 3.1, z: 1.0 },
      { id: "ENV-MTR-004", name: "East Mast Humidity Probe", domain: "ENVIRONMENT", type: "HUMIDITY", value: 58.0, unit: "%", status: "WARNING", quality: "DEGRADED", lastUpdate: "19:26:40 UTC", criticality: "MEDIUM", minValue: 10.0, maxValue: 100.0, x: 9.5, y: 2.8, z: 0.0 },
      { id: "ENG-MTR-001", name: "Solar Array Pyranometer", domain: "ENERGY", type: "IRRADIANCE", value: 420.0, unit: "W/m²", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:02 UTC", criticality: "MEDIUM", minValue: 0.0, maxValue: 1200.0, x: 0.0, y: 2.8, z: -7.2 },
      { id: "ENG-MTR-002", name: "DG-2 Vibration Accelerometer", domain: "ENERGY", type: "VIBRATION", value: 4.8, unit: "mm/s", status: "CRITICAL", quality: "DEGRADED", lastUpdate: "19:27:12 UTC", criticality: "CRITICAL", minValue: 0.0, maxValue: 3.5, x: -8.5, y: 2.2, z: -7.2 },
      { id: "ENG-MTR-003", name: "Battery Bank B Voltage Monitor", domain: "ENERGY", type: "VOLTAGE", value: 418.2, unit: "V", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:05 UTC", criticality: "HIGH", minValue: 380.0, maxValue: 440.0, x: 1.8, y: 2.2, z: -7.2 },
      { id: "ENG-MTR-004", name: "Wind Turbine Generator Load", domain: "ENERGY", type: "POWER", value: 18.4, unit: "kW", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:00 UTC", criticality: "HIGH", minValue: 0.0, maxValue: 50.0, x: 12.5, y: 3.2, z: -3.5 },
      { id: "STR-MTR-001", name: "Main Living Module Strain Gauge 1", domain: "STRUCTURE", type: "STRAIN", value: 142.0, unit: "με", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:48 UTC", criticality: "HIGH", minValue: 0.0, maxValue: 800.0, x: 0.0, y: 2.8, z: 0.0 },
      { id: "STR-MTR-002", name: "Stilt Foundation Thermal Sensor", domain: "STRUCTURE", type: "TEMPERATURE", value: -14.2, unit: "°C", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:30 UTC", criticality: "MEDIUM", minValue: -40.0, maxValue: 5.0, x: -4.2, y: 0.6, z: 2.8 },
      { id: "LOG-MTR-001", name: "Bulk Fuel Tank #1 Ultrasonic Level", domain: "LOGISTICS", type: "LEVEL", value: 64.0, unit: "%", status: "NORMAL", quality: "GOOD", lastUpdate: "19:25:10 UTC", criticality: "HIGH", minValue: 15.0, maxValue: 100.0, x: 8.5, y: 2.4, z: -7.2 },
      { id: "LOG-MTR-002", name: "Day Tank Flow Transducer", domain: "LOGISTICS", type: "FLOW", value: 0.0, unit: "L/min", status: "OFFLINE", quality: "OFFLINE", lastUpdate: "18:42:00 UTC", criticality: "LOW", minValue: 0.0, maxValue: 50.0, x: -6.0, y: 1.5, z: -7.2 }
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

    // 3D Digital Twin configuration with 6 required spatial zones arranged in modular connected layout
    digitalTwin: {
      model: "procedural-parametric",
      elevationStilts: true,
      zones: [
        { id: "Z-BHR-01", name: "MAIN BUILDING", code: "MAIN", position: [0, 1.8, 0], size: [13.5, 3.4, 7.5], shape: "box", color: "#ece8df", status: "NOMINAL", description: "Integrated aerodynamic habitat, remote sensing ops, and expedition command" },
        { id: "Z-BHR-02", name: "ENERGY", code: "ENERGY", position: [0, 1.5, -7.5], size: [6.5, 2.6, 5.0], shape: "box", color: "#dfd9ce", status: "NOMINAL", description: "Clean microgrid power management, LiFePO4 battery banks, and solar array bus" },
        { id: "Z-BHR-03", name: "RESEARCH", code: "RESEARCH", position: [10.5, 1.5, 0], size: [6.0, 2.6, 5.8], shape: "box", color: "#dfd9ce", status: "NOMINAL", description: "Cryosphere, oceanography, geomagnetism, and satellite earth observation labs" },
        { id: "Z-BHR-04", name: "STORAGE", code: "STORAGE", position: [9.5, 1.3, -7.5], size: [6.5, 2.3, 5.0], shape: "box", color: "#d6cfc3", status: "NOMINAL", description: "Scientific samples deep freezer, field equipment, and logistics containers" },
        { id: "Z-BHR-05", name: "GENERATOR", code: "GENERATOR", position: [-9.5, 1.3, -7.5], size: [6.2, 2.3, 5.0], shape: "box", color: "#d9d0c2", status: "NOMINAL", description: "Clean emission CHP generator plant, exhaust stacks, and waste heat recovery" },
        { id: "Z-BHR-06", name: "COMMS", code: "COMMS", position: [0, 3.8, -13.8], size: [2.4, 4.8, 2.4], shape: "cylinder", color: "#b65a1f", status: "NOMINAL", description: "Optical radome tracking GSAT-30, Starlink polar gateway, and RF mast" }
      ],
      sensors: []
    },

    // Comprehensive sensor registry configuration mapped to 3D station zones
    sensors: [
      { id: "ENV-BHR-001", name: "Larsemann Hills Optical Anemometer", domain: "ENVIRONMENT", type: "WIND_SPEED", value: 26.4, unit: "km/h", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:10 UTC", criticality: "HIGH", minValue: 0.0, maxValue: 180.0, x: 0.0, y: 7.5, z: -13.8 },
      { id: "ENV-BHR-002", name: "Surface Temperature Array", domain: "ENVIRONMENT", type: "TEMPERATURE", value: -12.6, unit: "°C", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:08 UTC", criticality: "HIGH", minValue: -45.0, maxValue: 15.0, x: 3.5, y: 3.6, z: 1.5 },
      { id: "ENV-BHR-003", name: "Digital Microbarometer", domain: "ENVIRONMENT", type: "PRESSURE", value: 994.5, unit: "hPa", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:50 UTC", criticality: "MEDIUM", minValue: 930.0, maxValue: 1050.0, x: -2.5, y: 3.6, z: 1.0 },
      { id: "ENG-BHR-001", name: "Clean Microgrid Solar Bus", domain: "ENERGY", type: "POWER", value: 54.2, unit: "kW", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:04 UTC", criticality: "HIGH", minValue: 0.0, maxValue: 80.0, x: 0.0, y: 3.0, z: -7.5 },
      { id: "ENG-BHR-002", name: "Lithium Iron Phosphate Battery SOH", domain: "ENERGY", type: "HEALTH", value: 99.4, unit: "%", status: "NORMAL", quality: "GOOD", lastUpdate: "19:28:00 UTC", criticality: "HIGH", minValue: 70.0, maxValue: 100.0, x: 1.8, y: 2.2, z: -7.5 },
      { id: "ENG-BHR-003", name: "Wind Turbine #2 Pitch Actuator", domain: "ENERGY", type: "ANGLE", value: 14.5, unit: "deg", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:35 UTC", criticality: "MEDIUM", minValue: 0.0, maxValue: 90.0, x: 13.0, y: 4.0, z: -3.5 },
      { id: "STR-BHR-001", name: "Integrated Pod Aerodynamic Load", domain: "STRUCTURE", type: "LOAD", value: 38.2, unit: "kN", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:42 UTC", criticality: "HIGH", minValue: 0.0, maxValue: 250.0, x: 0.0, y: 3.0, z: 3.2 },
      { id: "STR-BHR-002", name: "Structural Joint Expansion Gauge", domain: "STRUCTURE", type: "DISPLACEMENT", value: 0.85, unit: "mm", status: "NORMAL", quality: "GOOD", lastUpdate: "19:26:50 UTC", criticality: "LOW", minValue: 0.0, maxValue: 5.0, x: 6.8, y: 2.0, z: 0.0 },
      { id: "LOG-BHR-001", name: "Primary Polar Diesel Reserve", domain: "LOGISTICS", type: "LEVEL", value: 84.0, unit: "%", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:15 UTC", criticality: "HIGH", minValue: 20.0, maxValue: 100.0, x: 9.5, y: 2.5, z: -7.5 },
      { id: "LOG-BHR-002", name: "Waste Heat Glycol Circulation", domain: "LOGISTICS", type: "FLOW", value: 42.0, unit: "L/min", status: "NORMAL", quality: "GOOD", lastUpdate: "19:27:00 UTC", criticality: "MEDIUM", minValue: 10.0, maxValue: 60.0, x: -9.5, y: 2.0, z: -7.5 }
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
