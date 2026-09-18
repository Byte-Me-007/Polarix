import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { StationProvider } from './context/StationContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Sensors } from './pages/Sensors';
import { DigitalTwin } from './pages/DigitalTwin';
import { Alerts } from './pages/Alerts';
import { Energy } from './pages/Energy';
import { Logistics } from './pages/Logistics';
import { Events } from './pages/Events';
import { Settings } from './pages/Settings';
import { ModulePlaceholder } from './pages/ModulePlaceholder';
import './styles/dashboard.css';

export function App() {
  return (
    <StationProvider>
      <BrowserRouter>
        <div className="app-container">
          <Navbar />
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/digital-twin" element={<DigitalTwin />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/energy" element={<Energy />} />
            <Route path="/logistics" element={<Logistics />} />
            <Route path="/sensors" element={<Sensors />} />
            <Route path="/events" element={<Events />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </StationProvider>
  );
}

export default App;
