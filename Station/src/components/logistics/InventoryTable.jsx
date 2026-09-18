import React, { useState } from 'react';

/**
 * InventoryTable
 * Main operational inventory table with category tabs and compact visual stock bars.
 */
export const InventoryTable = ({
  inventory = [],
  onLocateInTwin
}) => {
  const [activeCategory, setActiveCategory] = useState('ALL');

  const categories = [
    'ALL',
    'FOOD',
    'MEDICAL',
    'FUEL',
    'SCIENTIFIC SUPPLIES',
    'SPARE PARTS',
    'EMERGENCY SUPPLIES'
  ];

  const filteredItems = activeCategory === 'ALL'
    ? inventory
    : inventory.filter((item) => item.category === activeCategory);

  return (
    <section className="inventory-status-card" aria-label="Inventory Status Table">
      <div className="card-header-row">
        <div>
          <h3 className="card-title">INVENTORY STATUS</h3>
          <span className="card-subtitle">
            STATION STORES, DAILY CONSUMPTION RATES & AUTONOMY BUFFERS
          </span>
        </div>
        <span className="card-tag">{filteredItems.length} ITEMS CATALOGED</span>
      </div>

      {/* Category Filter Tabs */}
      <div className="inventory-category-tabs" role="tablist">
        {categories.map((cat) => (
          <button
            key={cat}
            type="button"
            role="tab"
            aria-selected={activeCategory === cat}
            className={`category-tab-btn ${activeCategory === cat ? 'active' : ''}`}
            onClick={() => setActiveCategory(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* Table */}
      <div className="inventory-table-wrapper">
        <table className="inventory-table">
          <thead>
            <tr>
              <th scope="col">ITEM / CATEGORY</th>
              <th scope="col">STOCK LEVEL</th>
              <th scope="col">CURRENT STOCK</th>
              <th scope="col">DAILY CONSUMPTION</th>
              <th scope="col">REMAINING DAYS</th>
              <th scope="col">STATUS</th>
              <th scope="col">STORAGE LOCATION</th>
            </tr>
          </thead>
          <tbody>
            {filteredItems.map((item) => {
              const pct = item.capacity > 0
                ? Math.min(100, Math.round((item.stock / item.capacity) * 100))
                : 100;

              const isCrit = item.status === 'CRITICAL';
              const isWarn = item.status === 'WARNING';
              const statusColor = isCrit ? '#c82a2a' : isWarn ? '#d9821a' : '#3f6e4a';
              const barFillColor = isCrit ? '#c82a2a' : isWarn ? '#d9821a' : '#3f6e4a';

              return (
                <tr key={item.id} className="inventory-table-row">
                  <td className="item-name-cell">
                    <div className="item-title">{item.item}</div>
                    <span className="item-cat-badge">{item.category}</span>
                  </td>

                  {/* Stock Bar */}
                  <td className="item-bar-cell">
                    <div className="stock-bar-container">
                      <div className="stock-bar-track">
                        <div
                          className="stock-bar-fill"
                          style={{
                            width: `${pct}%`,
                            background: barFillColor
                          }}
                        />
                      </div>
                      <span className="stock-pct-label">{pct}%</span>
                    </div>
                  </td>

                  <td className="item-stock-cell">
                    <strong>{item.stock.toLocaleString()}</strong> <span className="unit-label">{item.unit}</span>
                  </td>

                  <td className="item-consumption-cell">
                    {item.dailyConsumption > 0 ? (
                      <span>{item.dailyConsumption} <span className="unit-label">{item.unit}/day</span></span>
                    ) : (
                      <span className="consumption-dormant">— (BUFFER)</span>
                    )}
                  </td>

                  <td className="item-days-cell">
                    {item.remainingDays < 900 ? (
                      <strong style={{ color: statusColor }}>
                        {item.remainingDays.toFixed(1)} DAYS
                      </strong>
                    ) : (
                      <span className="infinite-days">∞ STRATEGIC RESERVE</span>
                    )}
                  </td>

                  <td className="item-status-cell">
                    <span
                      className={`inventory-status-pill ${item.status.toLowerCase()}`}
                      style={{ color: statusColor, borderColor: statusColor }}
                    >
                      ● {item.status}
                    </span>
                  </td>

                  <td className="item-location-cell">
                    <span className="location-text">{item.location}</span>
                    {item.sensorRef && onLocateInTwin && (
                      <button
                        type="button"
                        className="table-twin-btn"
                        title="View storage area in 3D Digital Twin"
                        onClick={() => onLocateInTwin(item.sensorRef)}
                      >
                        ⌖
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default InventoryTable;
