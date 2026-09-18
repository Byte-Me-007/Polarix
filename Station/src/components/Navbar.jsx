import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import { StationSelector } from './StationSelector';
import { ConnectionStatus } from './ConnectionStatus';
import { useStationTelemetry } from '../hooks/useStationTelemetry';
import { useMissionReadiness } from '../hooks/useMissionReadiness';
import { MissionReadinessDrawer } from './readiness/MissionReadinessDrawer';

export const Navbar = () => {
  const { activeStation, config } = useStationTelemetry();
  const readiness = useMissionReadiness();
  const [isReadinessDrawerOpen, setIsReadinessDrawerOpen] = useState(false);
  const [currentTime, setCurrentTime] = useState(new Date());

  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Format UTC
  const utcString = currentTime.toLocaleTimeString('en-GB', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  // Format Station Local Time
  const localOffsetHours = config?.timeZoneOffsetHours ?? (activeStation === 'MAITRI' ? 1 : 5);
  const stationDate = new Date(currentTime.getTime() + localOffsetHours * 3600000);
  const stationLocalString = stationDate.toLocaleTimeString('en-GB', {
    timeZone: 'UTC',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  });

  const navItems = [
    { name: 'Dashboard', path: '/' },
    { name: 'Digital Twin', path: '/digital-twin' },
    { name: 'Alerts', path: '/alerts' },
    { name: 'Energy', path: '/energy' },
    { name: 'Logistics', path: '/logistics' },
    { name: 'Sensors', path: '/sensors' },
    { name: 'Events', path: '/events' },
    { name: 'Settings', path: '/settings' },
  ];

  return (
    <>
      <header className="top-navbar">
        <div className="top-navbar-inner">
          {/* LEFT: POLARIS / ANTARCTIC DIGITAL TWIN + Technical Identifier + Mission Readiness */}
          <div className="nav-brand-group">
            <NavLink to="/" className="polaris-brand">
              <span className="polaris-title">POLARIS</span>
              <span className="polaris-sub">ANTARCTIC DIGITAL TWIN</span>
            </NavLink>
            <span className="technical-stamp">SYS // IND-POL-26</span>

            {/* Global Operational Mission Readiness Indicator */}
            <button
              className={`nav-readiness-pill readiness-pill-${readiness.overallReadiness.toLowerCase().replace(' ', '-')}`}
              onClick={() => setIsReadinessDrawerOpen(true)}
              title={`Mission Readiness: ${readiness.overallReadiness}. Click to inspect contributing systems and causes.`}
            >
              <span className="nav-readiness-dot" />
              <span className="nav-readiness-title">READINESS:</span>
              <span className="nav-readiness-value">{readiness.overallReadiness}</span>
            </button>
          </div>

          {/* CENTER: Scientific Instrument Station Selector */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
            <StationSelector />

            {/* Navigation Links */}
            <nav aria-label="Main Navigation">
              <ul className="nav-links-menu">
                {navItems.map((item) => (
                  <li key={item.name}>
                    <NavLink
                      to={item.path}
                      className={({ isActive }) =>
                        `nav-link-item ${isActive ? 'active' : ''}`
                      }
                    >
                      {item.name}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </nav>
          </div>

          {/* RIGHT: SATELLITE UPLINK, UTC TIME, STATION LOCAL TIME */}
          <div className="nav-right-status">
            <ConnectionStatus />
            <span className="nav-status-sep">|</span>

            <div className="time-readout">
              <span className="time-label">UTC TIME</span>
              <span className="time-val">{utcString}</span>
            </div>

            <span className="nav-status-sep">|</span>

            <div className="time-readout">
              <span className="time-label">{activeStation} LOCAL (UTC+{localOffsetHours})</span>
              <span className="time-val">{stationLocalString}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Global Mission Readiness Slide-in Drawer */}
      <MissionReadinessDrawer
        isOpen={isReadinessDrawerOpen}
        onClose={() => setIsReadinessDrawerOpen(false)}
      />
    </>
  );
};

export default Navbar;
