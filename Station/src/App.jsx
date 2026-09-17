import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { StationProvider } from './context/StationContext';
import { Navbar } from './components/Navbar';
import { Dashboard } from './pages/Dashboard';
import { Sensors } from './pages/Sensors';
import { DigitalTwin } from './pages/DigitalTwin';
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
            <Route path="/alerts" element={<ModulePlaceholder />} />
            <Route path="/energy" element={<ModulePlaceholder />} />
            <Route path="/logistics" element={<ModulePlaceholder />} />
            <Route path="/sensors" element={<Sensors />} />
            <Route path="/events" element={<ModulePlaceholder />} />
            <Route path="/settings" element={<ModulePlaceholder />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </StationProvider>
  );
}

export default App;
