import React from 'react';

/**
 * CargoManifestModal
 * Clean operational modal displaying the itemized cargo manifest for an incoming shipment.
 */
export const CargoManifestModal = ({
  mission,
  onClose
}) => {
  if (!mission) return null;

  const manifest = mission.manifest || [];

  return (
    <div className="manifest-modal-backdrop" onClick={onClose} role="dialog" aria-modal="true">
      <div className="manifest-modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="manifest-modal-header">
          <div>
            <div className="manifest-mission-badge">CARGO MANIFEST // {mission.missionId}</div>
            <h3 className="manifest-modal-title">{mission.transport}</h3>
            <span className="manifest-modal-sub">
              Route: {mission.origin} ➔ {mission.destination} | Total Payload: {mission.weightTons} t
            </span>
          </div>
          <button
            type="button"
            className="manifest-close-btn"
            onClick={onClose}
            aria-label="Close cargo manifest"
          >
            ✕
          </button>
        </div>

        <div className="manifest-table-wrapper">
          <table className="manifest-table">
            <thead>
              <tr>
                <th scope="col">CATEGORY</th>
                <th scope="col">ITEM DESCRIPTION</th>
                <th scope="col">QUANTITY</th>
                <th scope="col">WEIGHT</th>
                <th scope="col">PRIORITY</th>
              </tr>
            </thead>
            <tbody>
              {manifest.length === 0 ? (
                <tr>
                  <td colSpan="5" className="manifest-empty">
                    Manifest pending automated loadmaster sign-off at origin staging depot.
                  </td>
                </tr>
              ) : (
                manifest.map((item, idx) => {
                  const isCrit = item.priority === 'CRITICAL';
                  const isHigh = item.priority === 'HIGH';
                  const color = isCrit ? '#c82a2a' : isHigh ? '#d9821a' : '#3f6e4a';

                  return (
                    <tr key={idx}>
                      <td className="manifest-cat-cell">
                        <span className="cat-pill">{item.category}</span>
                      </td>
                      <td className="manifest-item-cell">
                        <strong>{item.item}</strong>
                      </td>
                      <td className="manifest-qty-cell">
                        {item.quantity.toLocaleString()} {item.unit}
                      </td>
                      <td className="manifest-weight-cell">
                        {item.weightKg} kg
                      </td>
                      <td className="manifest-prio-cell">
                        <span
                          className="prio-badge"
                          style={{
                            color,
                            borderColor: color,
                            background: isCrit ? 'rgba(200,42,42,0.08)' : isHigh ? 'rgba(217,130,26,0.08)' : 'rgba(63,110,74,0.08)'
                          }}
                        >
                          ● {item.priority}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        <div className="manifest-modal-footer">
          <div className="manifest-footer-info">
            ETA: <strong>{mission.etaDays} DAYS</strong> • Confidence: <strong>{mission.confidence}</strong>
          </div>
          <button
            type="button"
            className="manifest-done-btn"
            onClick={onClose}
          >
            CLOSE MANIFEST
          </button>
        </div>
      </div>
    </div>
  );
};

export default CargoManifestModal;
