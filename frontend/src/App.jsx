import { useState, useEffect } from 'react';
import { Truck, ShieldCheck, MapPin, AlertCircle, List } from 'lucide-react';
import TripForm from './components/TripForm';
import TripSummary from './components/TripSummary';
import RouteMap from './components/RouteMap';
import EldLogViewer from './components/EldLogViewer';
import EventTimeline from './components/EventTimeline';
import { fetchPlanTrip } from './services/api';

export default function App() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [tripData, setTripData] = useState(null);
  const [metaData, setMetaData] = useState({
    driver_name: '',
    carrier_name: '',
    truck_number: '',
    trailer_number: ''
  });

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

    const {
      driver_name = '',
      carrier_name = '',
      truck_number = '',
      trailer_number = '',
      ...apiParams
    } = params;

    try {
      const data = await fetchPlanTrip(apiParams);
      setTripData(data);
      setMetaData({
        driver_name: (driver_name || '').trim(),
        carrier_name: (carrier_name || '').trim(),
        truck_number: (truck_number || '').trim(),
        trailer_number: (trailer_number || '').trim()
      });
    } catch (err) {
      setTripData(null);
      setMetaData({ driver_name: '', carrier_name: '', truck_number: '', trailer_number: '' });
      setError(err.message || 'Failed to calculate trip route and HOS schedule.');
    } finally {
      setLoading(false);
    }
  };

  // Collect key event waypoints from route data for the timeline
  const timelineWaypoints = tripData?.route?.waypoints || [];

  return (
    <div className="app-container">
      {/* Header Bar */}
      <header className="app-header">
        <div className="logo-group">
          <div className="logo-icon">
            <Truck size={22} />
          </div>
          <div>
            <h1 className="app-title">Spotter AI HOS &amp; Route Planner</h1>
            <p className="app-subtitle">FMCSA Property Carrier Hours of Service &amp; ELD Log Generator</p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--success)', fontSize: '0.8rem', fontWeight: 600 }}>
          <ShieldCheck size={16} />
          FMCSA April 2022 Compliant
        </div>
      </header>

      {/* Loading Overlay */}
      {loading && (
        <div className="loading-overlay">
          <div className="loading-spinner-wrapper">
            <div className="loading-spinner" />
            <div className="loading-text">
              <div style={{ fontWeight: 700, fontSize: '1rem', color: '#fff', marginBottom: '4px' }}>
                Calculating Route &amp; HOS Schedule
              </div>
              <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                Geocoding locations · Planning route · Applying FMCSA rules · Generating ELD logs
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Main Grid */}
      <main className="main-layout">
        {/* Left Column: Input Form */}
        <aside>
          <TripForm onSubmit={handlePlanTrip} loading={loading} />
        </aside>

        {/* Right Column: Results */}
        <section>
          {error && (
            <div className="error-banner" role="alert">
              <AlertCircle size={18} style={{ display: 'inline', marginRight: '8px', flexShrink: 0 }} />
              <div>
                <strong>Planning Error</strong>
                <div style={{ marginTop: '2px', fontSize: '0.8rem', opacity: 0.85 }}>{error}</div>
              </div>
            </div>
          )}

          {tripData && (
            <>
              {/* Trip Overview Metrics */}
              <TripSummary summary={tripData.summary} />

              {/* Route Map */}
              <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.5rem' }}>
                <h3 className="panel-title" style={{ fontSize: '0.95rem', marginBottom: '0.75rem' }}>
                  <MapPin size={17} className="text-primary" />
                  Route Map &amp; Planned Stop Waypoints
                </h3>
                <RouteMap route={tripData.route} />
              </div>

              {/* HOS Event Timeline */}
              {timelineWaypoints.length > 0 && (
                <div className="glass-panel" style={{ padding: '1rem', marginBottom: '1.5rem' }}>
                  <h3 className="panel-title" style={{ fontSize: '0.95rem', marginBottom: '0.75rem' }}>
                    <List size={17} className="text-primary" />
                    Trip Event Timeline
                  </h3>
                  <EventTimeline waypoints={timelineWaypoints} />
                </div>
              )}

              {/* ELD Daily Logs */}
              <div className="glass-panel">
                <EldLogViewer dailyLogs={tripData.daily_logs} metaData={metaData} />
              </div>
            </>
          )}
        </section>
      </main>
    </div>
  );
}
