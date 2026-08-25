import { useState, useEffect } from 'react';
import { Truck, ShieldCheck, MapPin, AlertCircle } from 'lucide-react';
import TripForm from './components/TripForm';
import TripSummary from './components/TripSummary';
import RouteMap from './components/RouteMap';
import EldLogViewer from './components/EldLogViewer';
import { fetchPlanTrip } from './services/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tripData, setTripData] = useState(null);

  // Auto-load default trip on mount
  useEffect(() => {
    handlePlanTrip({
      current_location: 'Chicago, IL',
      pickup_location: 'Indianapolis, IN',
      dropoff_location: 'Dallas, TX',
      current_cycle_used: 15
    });
  }, []);

  const handlePlanTrip = async (params) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPlanTrip(params);
      setTripData(data);
    } catch (err) {
      setTripData(null);
      setError(err.message || 'Failed to calculate trip route and HOS schedule.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="app-header">
        <div className="logo-group">
          <div className="logo-icon">
            <Truck size={24} />
          </div>
          <div>
            <h1 className="app-title">Spotter AI HOS & Route Planner</h1>
            <p className="app-subtitle">FMCSA Property Carrier Hours of Service & ELD Log Generator</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--success)', fontSize: '0.85rem', fontWeight: 600 }}>
          <ShieldCheck size={18} />
          FMCSA April 2022 Compliant
        </div>
      </header>

      {/* Main Grid */}
      <main className="main-layout">
        {/* Left Column: Input Form */}
        <aside>
          <TripForm onSubmit={handlePlanTrip} loading={loading} />
        </aside>

        {/* Right Column: Route Map, Metrics & ELD Logs */}
        <section>
          {error && (
            <div className="error-banner">
              <AlertCircle size={18} style={{ display: 'inline', marginRight: '6px' }} />
              {error}
            </div>
          )}

          {tripData && (
            <>
              <TripSummary summary={tripData.summary} />
              
              <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.5rem' }}>
                <h3 className="panel-title" style={{ fontSize: '1rem', marginBottom: '0.75rem' }}>
                  <MapPin size={18} className="text-primary" />
                  Route Map & Planned Stop Waypoints
                </h3>
                <RouteMap route={tripData.route} />
              </div>

              <div className="glass-panel">
                <EldLogViewer dailyLogs={tripData.daily_logs} />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
