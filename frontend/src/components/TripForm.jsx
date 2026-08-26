import { useState } from 'react';
import { Navigation, Play, Zap, AlertCircle } from 'lucide-react';

export default function TripForm({ onSubmit, loading }) {
  const [currentLocation, setCurrentLocation] = useState('Chicago, IL');
  const [pickupLocation, setPickupLocation] = useState('Indianapolis, IN');
  const [dropoffLocation, setDropoffLocation] = useState('Dallas, TX');
  const [currentCycleUsed, setCurrentCycleUsed] = useState('15');

  // Optional ELD Header Metadata
  const [driverName, setDriverName] = useState('');
  const [carrierName, setCarrierName] = useState('');
  const [truckNumber, setTruckNumber] = useState('');
  const [trailerNumber, setTrailerNumber] = useState('');

  const [validationError, setValidationError] = useState(null);

  const handleSubmit = (e) => {
    e.preventDefault();
    setValidationError(null);

    const current = currentLocation.trim();
    const pickup = pickupLocation.trim();
    const dropoff = dropoffLocation.trim();

    if (!current || !pickup || !dropoff) {
      setValidationError('Please enter valid, non-empty locations for all fields.');
      return;
    }

    const cycleNum = parseFloat(currentCycleUsed);
    if (isNaN(cycleNum) || cycleNum < 0 || cycleNum > 70) {
      setValidationError('Current Cycle Used must be a number between 0 and 70 hours.');
      return;
    }

    onSubmit({
      current_location: current,
      pickup_location: pickup,
      dropoff_location: dropoff,
      current_cycle_used: cycleNum,
      driver_name: driverName.trim(),
      carrier_name: carrierName.trim(),
      truck_number: truckNumber.trim(),
      trailer_number: trailerNumber.trim()
    });
  };

  const loadPreset = (current, pickup, dropoff, cycle) => {
    if (loading) return;
    setValidationError(null);
    setCurrentLocation(current);
    setPickupLocation(pickup);
    setDropoffLocation(dropoff);
    setCurrentCycleUsed(cycle.toString());
  };

  return (
    <div className="glass-panel">
      <h2 className="panel-title">
        <Navigation size={20} className="text-primary" />
        Trip Parameters
      </h2>

      <div className="form-group">
        <label className="form-label">Presets</label>
        <div className="preset-buttons">
          <button 
            type="button" 
            className="btn-preset"
            disabled={loading}
            onClick={() => loadPreset('Chicago, IL', 'Chicago, IL', 'Indianapolis, IN', 10)}
          >
            <Zap size={12} style={{ display: 'inline', marginRight: '4px' }} />
            Short (~180 mi)
          </button>
          <button 
            type="button" 
            className="btn-preset"
            disabled={loading}
            onClick={() => loadPreset('Chicago, IL', 'Indianapolis, IN', 'Dallas, TX', 15)}
          >
            <Zap size={12} style={{ display: 'inline', marginRight: '4px' }} />
            Medium (~1,120 mi)
          </button>
          <button 
            type="button" 
            className="btn-preset"
            disabled={loading}
            onClick={() => loadPreset('New York, NY', 'Atlanta, GA', 'Los Angeles, CA', 45)}
          >
            <Zap size={12} style={{ display: 'inline', marginRight: '4px' }} />
            Long (~2,800 mi)
          </button>
        </div>
      </div>

      {validationError && (
        <div className="error-banner" style={{ marginBottom: '1.25rem', fontSize: '0.85rem' }}>
          <AlertCircle size={16} style={{ display: 'inline', marginRight: '6px' }} />
          {validationError}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label" htmlFor="current_location">Current Location</label>
          <input
            id="current_location"
            type="text"
            className="form-input"
            placeholder="e.g. Chicago, IL"
            value={currentLocation}
            onChange={(e) => {
              setValidationError(null);
              setCurrentLocation(e.target.value);
            }}
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="pickup_location">Pickup Location</label>
          <input
            id="pickup_location"
            type="text"
            className="form-input"
            placeholder="e.g. Indianapolis, IN"
            value={pickupLocation}
            onChange={(e) => {
              setValidationError(null);
              setPickupLocation(e.target.value);
            }}
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="dropoff_location">Dropoff Location</label>
          <input
            id="dropoff_location"
            type="text"
            className="form-input"
            placeholder="e.g. Dallas, TX"
            value={dropoffLocation}
            onChange={(e) => {
              setValidationError(null);
              setDropoffLocation(e.target.value);
            }}
            disabled={loading}
            required
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="current_cycle_used">Current Cycle Used (Hours)</label>
          <input
            id="current_cycle_used"
            type="number"
            step="0.5"
            min="0"
            max="70"
            className="form-input"
            placeholder="0 to 70"
            value={currentCycleUsed}
            onChange={(e) => {
              setValidationError(null);
              setCurrentCycleUsed(e.target.value);
            }}
            disabled={loading}
            required
          />
        </div>

        {/* Optional ELD Log Header Metadata Section */}
        <div className="form-section-divider">
          <div className="form-section-label">Driver &amp; Carrier Metadata (Optional)</div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem', marginBottom: '0.6rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="driver_name">Driver Name</label>
              <input
                id="driver_name"
                type="text"
                className="form-input"
                placeholder="e.g. John Smith"
                value={driverName}
                onChange={(e) => setDriverName(e.target.value)}
                disabled={loading}
                autoComplete="name"
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="carrier_name">Carrier Name</label>
              <input
                id="carrier_name"
                type="text"
                className="form-input"
                placeholder="e.g. Spotter Logistics"
                value={carrierName}
                onChange={(e) => setCarrierName(e.target.value)}
                disabled={loading}
                autoComplete="organization"
              />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.6rem' }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="truck_number">Truck #</label>
              <input
                id="truck_number"
                type="text"
                className="form-input"
                placeholder="e.g. TRK-104"
                value={truckNumber}
                onChange={(e) => setTruckNumber(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label className="form-label" htmlFor="trailer_number">Trailer #</label>
              <input
                id="trailer_number"
                type="text"
                className="form-input"
                placeholder="e.g. TRL-882"
                value={trailerNumber}
                onChange={(e) => setTrailerNumber(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          className="btn-submit"
          disabled={loading}
          aria-label={loading ? 'Processing route and HOS schedule' : 'Calculate route and generate ELD logs'}
        >
          {loading ? (
            <span>Processing Route &amp; HOS...</span>
          ) : (
            <>
              <Play size={18} aria-hidden="true" />
              Calculate Route &amp; ELD Logs
            </>
          )}
        </button>
      </form>
    </div>
  );
}
