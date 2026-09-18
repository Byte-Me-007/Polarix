/**
 * logisticsData.js
 * Comprehensive Antarctic Expedition Logistics & Supply Chain datasets for
 * MAITRI and BHARATI research stations.
 * 
 * Data models support:
 * - Categorized Inventory with burn rates and days remaining
 * - Resupply Missions and Cargo Manifests
 * - Storage Facility Capacities and Utilization
 * - Route Risk & Transport Conditions
 */

export const LOGISTICS_DATA = {
  MAITRI: {
    // Executive Overview Totals
    summary: {
      totalInventoryTons: 128.4,
      criticalStockCount: 3,
      minDaysOfSupply: 18.4, // Constrained by fuel burn rate / oxygen
      incomingCargoTons: 18.6,
      storageUtilizationPct: 68
    },

    // Next upcoming mission ETA in days
    nextResupplyEtaDays: 14,
    nextResupplyMissionId: "RESUPPLY-07",
    nextResupplyTransport: "LC-130 HERCULES AIRCRAFT",

    // Categorized Inventory Items
    inventory: [
      // 1. FOOD
      {
        id: "INV-MTR-FOOD-01",
        category: "FOOD",
        item: "Deep-Frozen Protein Rations (Meat/Fish/Poultry)",
        stock: 3240,
        unit: "kg",
        capacity: 4500,
        dailyConsumption: 48,
        remainingDays: 67.5,
        status: "NORMAL",
        priority: "NORMAL",
        location: "Cold Storage Bay 1",
        sensorRef: "LOG-MTR-004"
      },
      {
        id: "INV-MTR-FOOD-02",
        category: "FOOD",
        item: "Dry Staples & Carbohydrates (Flour/Rice/Grains)",
        stock: 4820,
        unit: "kg",
        capacity: 6000,
        dailyConsumption: 118,
        remainingDays: 40.8,
        status: "NORMAL",
        priority: "NORMAL",
        location: "Dry Goods Pantry Container",
        sensorRef: "LOG-MTR-004"
      },
      {
        id: "INV-MTR-FOOD-03",
        category: "FOOD",
        item: "Hydroponic Greenhouse Nutrient Packs",
        stock: 185,
        unit: "kg",
        capacity: 350,
        dailyConsumption: 4.2,
        remainingDays: 44.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Greenhouse Biosphere",
        sensorRef: "LOG-MTR-004"
      },

      // 2. MEDICAL
      {
        id: "INV-MTR-MED-01",
        category: "MEDICAL",
        item: "Medical Oxygen Cylinders (50L / 200 bar)",
        stock: 14,
        unit: "cylinders",
        capacity: 40,
        dailyConsumption: 1.1,
        remainingDays: 12.7,
        status: "CRITICAL",
        priority: "CRITICAL",
        location: "Medical Infirmary Bay",
        sensorRef: "LOG-MTR-004"
      },
      {
        id: "INV-MTR-MED-02",
        category: "MEDICAL",
        item: "Hypothermia & Trauma Treatment Packs",
        stock: 42,
        unit: "kits",
        capacity: 60,
        dailyConsumption: 0.3,
        remainingDays: 140.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Infirmary Trauma Locker",
        sensorRef: "LOG-MTR-004"
      },
      {
        id: "INV-MTR-MED-03",
        category: "MEDICAL",
        item: "Antibiotics & Emergency Pharmaceuticals",
        stock: 620,
        unit: "doses",
        capacity: 1200,
        dailyConsumption: 22,
        remainingDays: 28.2,
        status: "WARNING",
        priority: "HIGH",
        location: "Controlled Dispensary Safe",
        sensorRef: "LOG-MTR-004"
      },

      // 3. FUEL
      {
        id: "INV-MTR-FUEL-01",
        category: "FUEL",
        item: "Arctic Diesel (SAB-55 Low Viscosity)",
        stock: 53400,
        unit: "L",
        capacity: 83400,
        dailyConsumption: 480,
        remainingDays: 18.4,
        status: "WARNING",
        priority: "CRITICAL",
        location: "Bulk Tank Farm Alpha",
        sensorRef: "LOG-MTR-001"
      },
      {
        id: "INV-MTR-FUEL-02",
        category: "FUEL",
        item: "Aviation Turbine Kerosene (Jet A-1 Anti-Freeze)",
        stock: 14200,
        unit: "L",
        capacity: 22000,
        dailyConsumption: 160,
        remainingDays: 88.7,
        status: "NORMAL",
        priority: "HIGH",
        location: "Helipad Fuel Depot",
        sensorRef: "LOG-MTR-001"
      },

      // 4. SCIENTIFIC SUPPLIES
      {
        id: "INV-MTR-SCI-01",
        category: "SCIENTIFIC SUPPLIES",
        item: "Cryogenic Liquid Nitrogen (LN2 Dewar Flasks)",
        stock: 450,
        unit: "L",
        capacity: 800,
        dailyConsumption: 12.5,
        remainingDays: 36.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Ice Core Storage Locker",
        sensorRef: "LOG-MTR-004"
      },
      {
        id: "INV-MTR-SCI-02",
        category: "SCIENTIFIC SUPPLIES",
        item: "Aerosol Sampler Fluoropore Filter Membranes",
        stock: 120,
        unit: "packs",
        capacity: 300,
        dailyConsumption: 4.5,
        remainingDays: 26.6,
        status: "WARNING",
        priority: "NORMAL",
        location: "Atmospheric Science Lab",
        sensorRef: "LOG-MTR-004"
      },

      // 5. SPARE PARTS
      {
        id: "INV-MTR-SPR-01",
        category: "SPARE PARTS",
        item: "DG Unit #2 Primary Fuel Filter Cartridges",
        stock: 6,
        unit: "units",
        capacity: 24,
        dailyConsumption: 0.65,
        remainingDays: 9.2,
        status: "CRITICAL",
        priority: "CRITICAL",
        location: "Generator Workshop Annex",
        sensorRef: "LOG-MTR-002"
      },
      {
        id: "INV-MTR-SPR-02",
        category: "SPARE PARTS",
        item: "Wind Turbine Dynamic Pitch Bearings",
        stock: 4,
        unit: "sets",
        capacity: 8,
        dailyConsumption: 0.05,
        remainingDays: 80.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Engineering Spares Bay",
        sensorRef: "LOG-MTR-004"
      },

      // 6. EMERGENCY SUPPLIES
      {
        id: "INV-MTR-EMG-01",
        category: "EMERGENCY SUPPLIES",
        item: "Extreme Cold Survival Blizzard Tents (4-Man)",
        stock: 12,
        unit: "tents",
        capacity: 16,
        dailyConsumption: 0.0,
        remainingDays: 999.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Emergency Survival Container",
        sensorRef: "LOG-MTR-004"
      },
      {
        id: "INV-MTR-EMG-02",
        category: "EMERGENCY SUPPLIES",
        item: "Immersion Cold-Water Rescue Suits",
        stock: 28,
        unit: "suits",
        capacity: 32,
        dailyConsumption: 0.0,
        remainingDays: 999.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Emergency Survival Container",
        sensorRef: "LOG-MTR-004"
      }
    ],

    // Storage Facilities Capacity Breakdown
    storageFacilities: [
      { name: "MAIN STORAGE CONTAINER BAY", usedTons: 68.0, capacityTons: 100.0, unit: "t", utilizationPct: 68, sensorRef: "LOG-MTR-004" },
      { name: "POLAR BULK FUEL FARM", usedTons: 44.8, capacityTons: 70.0, unit: "t", utilizationPct: 64, sensorRef: "LOG-MTR-001" },
      { name: "COLD STORAGE FREEZER BAY", usedTons: 8.2, capacityTons: 12.0, unit: "t", utilizationPct: 68, sensorRef: "LOG-MTR-004" },
      { name: "SCIENTIFIC SAMPLES CRYO DEPOT", usedTons: 4.5, capacityTons: 8.0, unit: "t", utilizationPct: 56, sensorRef: "LOG-MTR-004" },
      { name: "EMERGENCY BUFFER BUNKER", usedTons: 2.9, capacityTons: 5.0, unit: "t", utilizationPct: 58, sensorRef: "LOG-MTR-004" }
    ],

    // Upcoming Resupply Missions
    resupplyMissions: [
      {
        missionId: "RESUPPLY-07",
        transport: "LC-130 HERCULES SKI-AIRCRAFT",
        origin: "CAPE TOWN LOGISTICS HUB / NOVO AIRSTRIP",
        destination: "MAITRI STATION (MTR)",
        cargoSummary: "Medical Oxygen + Dry Food Rations + DG Fuel Filters",
        weightTons: 18.6,
        etaDays: 14,
        status: "IN TRANSIT",
        confidence: "HIGH (92%)",
        manifest: [
          { category: "MEDICAL", item: "Medical Oxygen Cylinders (50L)", quantity: 20, unit: "cylinders", weightKg: 1400, priority: "CRITICAL" },
          { category: "FOOD", item: "Cryo-Dehydrated Emergency Meals", quantity: 300, unit: "boxes", weightKg: 3600, priority: "HIGH" },
          { category: "SPARE PARTS", item: "DG Primary Fuel Filter Cartridges", quantity: 24, unit: "units", weightKg: 280, priority: "CRITICAL" },
          { category: "SCIENTIFIC", item: "Micro-Meteorological Sensor Probes", quantity: 12, unit: "units", weightKg: 140, priority: "NORMAL" },
          { category: "EMERGENCY", item: "Thermal Sub-Zero Over-boots", quantity: 50, unit: "pairs", weightKg: 210, priority: "NORMAL" }
        ]
      },
      {
        missionId: "CARGO-MTR-08",
        transport: "PISTENBULLY HEAVY SLEDGE CONVOY",
        origin: "INDIAN BARRIER ICE SHELF HARBOR",
        destination: "MAITRI STATION (MTR)",
        cargoSummary: "Arctic Diesel SAB-55 Fuel Bladders + Heavy Spares",
        weightTons: 34.0,
        etaDays: 32,
        status: "LOADING",
        confidence: "MEDIUM (78%)",
        manifest: [
          { category: "FUEL", item: "Arctic Diesel SAB-55 (Drummed)", quantity: 180, unit: "drums", weightKg: 28000, priority: "CRITICAL" },
          { category: "SPARE PARTS", item: "Generator Alternator Stator Assembly", quantity: 1, unit: "crate", weightKg: 2400, priority: "HIGH" },
          { category: "FOOD", item: "Long-Life Canned Proteins & Legumes", quantity: 150, unit: "cases", weightKg: 3600, priority: "NORMAL" }
        ]
      },
      {
        missionId: "POLAR-EXP-09",
        transport: "POLAR RESEARCH VESSEL S.A. AGULHAS II",
        origin: "GOA / CAPE TOWN",
        destination: "MAITRI STAGING ANCHORAGE",
        cargoSummary: "Annual Expedition Resupply & Personnel Rotation",
        weightTons: 140.0,
        etaDays: 78,
        status: "PLANNED",
        confidence: "PLANNED (85%)",
        manifest: [
          { category: "FUEL", item: "Bulk SAB-55 Antarctic Fuel Bunker", quantity: 80000, unit: "L", weightKg: 68000, priority: "CRITICAL" },
          { category: "FOOD", item: "Comprehensive 12-Month Food Stores", quantity: 1200, unit: "cases", weightKg: 42000, priority: "HIGH" },
          { category: "SCIENTIFIC", item: "Atmospheric Laser Lidar System", quantity: 4, unit: "cases", weightKg: 6500, priority: "HIGH" }
        ]
      }
    ],

    // Route & Weather Impact
    deliveryConditions: {
      routeStatus: "AIR CORRIDOR OPEN",
      deliveryRisk: "LOW",
      weatherImpact: "Clear skies over Schirmacher Oasis; katabatic wind speed 24 km/h",
      etaConfidence: "94% (ON SCHEDULE)"
    }
  },

  BHARATI: {
    summary: {
      totalInventoryTons: 164.2,
      criticalStockCount: 1,
      minDaysOfSupply: 34.2,
      incomingCargoTons: 26.4,
      storageUtilizationPct: 62
    },

    nextResupplyEtaDays: 22,
    nextResupplyMissionId: "BHR-CARGO-12",
    nextResupplyTransport: "ICEBREAKER RESEARCH VESSEL",

    inventory: [
      {
        id: "INV-BHR-FOOD-01",
        category: "FOOD",
        item: "Freeze-Dried Rations & Deep Freeze Stores",
        stock: 6400,
        unit: "kg",
        capacity: 8000,
        dailyConsumption: 142,
        remainingDays: 45.0,
        status: "NORMAL",
        priority: "NORMAL",
        location: "Main Food Storage Pod",
        sensorRef: "LOG-BHR-004"
      },
      {
        id: "INV-BHR-MED-01",
        category: "MEDICAL",
        item: "Medical Oxygen & Anaesthetic Gas Cylinders",
        stock: 22,
        unit: "cylinders",
        capacity: 45,
        dailyConsumption: 1.2,
        remainingDays: 18.3,
        status: "WARNING",
        priority: "CRITICAL",
        location: "Infirmary Oxygen Room",
        sensorRef: "LOG-BHR-004"
      },
      {
        id: "INV-BHR-MED-02",
        category: "MEDICAL",
        item: "Pharmaceutical Buffer & Sterile Surgical Packs",
        stock: 890,
        unit: "doses",
        capacity: 1500,
        dailyConsumption: 26,
        remainingDays: 34.2,
        status: "NORMAL",
        priority: "HIGH",
        location: "Medical Pod B",
        sensorRef: "LOG-BHR-004"
      },
      {
        id: "INV-BHR-FUEL-01",
        category: "FUEL",
        item: "Arctic Marine Diesel (Larsmann SAB)",
        stock: 88200,
        unit: "L",
        capacity: 105000,
        dailyConsumption: 510,
        remainingDays: 164.0,
        status: "NORMAL",
        priority: "CRITICAL",
        location: "Double-Walled Tank Bay",
        sensorRef: "LOG-BHR-001"
      },
      {
        id: "INV-BHR-SCI-01",
        category: "SCIENTIFIC SUPPLIES",
        item: "Ice Core Cryogenic Preservation Vials",
        stock: 840,
        unit: "vials",
        capacity: 2000,
        dailyConsumption: 42,
        remainingDays: 20.0,
        status: "WARNING",
        priority: "HIGH",
        location: "Cryo Storage Locker",
        sensorRef: "LOG-BHR-004"
      },
      {
        id: "INV-BHR-SPR-01",
        category: "SPARE PARTS",
        item: "Desalination RO High-Pressure Membranes",
        stock: 2,
        unit: "modules",
        capacity: 10,
        dailyConsumption: 0.22,
        remainingDays: 9.1,
        status: "CRITICAL",
        priority: "CRITICAL",
        location: "Utility Workshop",
        sensorRef: "LOG-BHR-003"
      },
      {
        id: "INV-BHR-EMG-01",
        category: "EMERGENCY SUPPLIES",
        item: "Immersion Evacuation Suits & EPIRBs",
        stock: 45,
        unit: "suits",
        capacity: 50,
        dailyConsumption: 0.0,
        remainingDays: 999.0,
        status: "NORMAL",
        priority: "HIGH",
        location: "Safety Locker Bay",
        sensorRef: "LOG-BHR-004"
      }
    ],

    storageFacilities: [
      { name: "CONTAINER LOGISTICS POD", usedTons: 74.0, capacityTons: 120.0, unit: "t", utilizationPct: 62, sensorRef: "LOG-BHR-004" },
      { name: "COASTAL FUEL FARM (LARSEMANN)", usedTons: 74.0, capacityTons: 95.0, unit: "t", utilizationPct: 78, sensorRef: "LOG-BHR-001" },
      { name: "SAMPLE CRYO-LOCKER ANNEX", usedTons: 9.2, capacityTons: 15.0, unit: "t", utilizationPct: 61, sensorRef: "LOG-BHR-004" },
      { name: "REVERSE OSMOSIS WATER DEPOT", usedTons: 6.8, capacityTons: 10.0, unit: "t", utilizationPct: 68, sensorRef: "LOG-BHR-003" }
    ],

    resupplyMissions: [
      {
        missionId: "BHR-CARGO-12",
        transport: "ICEBREAKER RESEARCH VESSEL",
        origin: "FREMANTLE / CAPE TOWN",
        destination: "BHARATI STATION (BHR)",
        cargoSummary: "Desalination RO Membranes + Cryo Vials + Food",
        weightTons: 26.4,
        etaDays: 22,
        status: "IN TRANSIT",
        confidence: "HIGH (90%)",
        manifest: [
          { category: "SPARE PARTS", item: "Desalination RO Membrane Cartridges", quantity: 8, unit: "modules", weightKg: 340, priority: "CRITICAL" },
          { category: "SCIENTIFIC", item: "Liquid Helium Cryostat Spares", quantity: 6, unit: "dewars", weightKg: 850, priority: "HIGH" },
          { category: "FOOD", item: "Long-Life Vitamin-Enriched Provisions", quantity: 240, unit: "cases", weightKg: 4800, priority: "NORMAL" }
        ]
      }
    ],

    deliveryConditions: {
      routeStatus: "COASTAL ICE PACK NAVIGABLE",
      deliveryRisk: "LOW",
      weatherImpact: "Sea ice concentration 4/10; offshore swell 1.4m",
      etaConfidence: "91% (ON SCHEDULE)"
    }
  }
};
