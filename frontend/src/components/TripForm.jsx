import { useState } from 'react';
import { Navigation, Play, Zap } from 'lucide-react';

export default function TripForm({ onSubmit, loading }) {
  const [currentLocation, setCurrentLocation] = useState('Chicago, IL');
  const [pickupLocation, setPickupLocation] = useState('Indianapolis, IN');
  const [dropoffLocation, setDropoffLocation] = useState('Dallas, TX');
  const [currentCycleUsed, setCurrentCycleUsed] = useState('15');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!currentLocation || !pickupLocation || !dropoffLocation) return;
    
    onSubmit({
      current_location: currentLocation,
      pickup_location: pickupLocation,
      dropoff_location: dropoffLocation,
      current_cycle_used: parseFloat(currentCycleUsed) || 0
    });
  };

  const loadPreset = (current, pickup, dropoff, cycle) => {
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
            onClick={() => loadPreset('Chicago, IL', 'Chicago, IL', 'Indianapolis, IN', 10)}
          >
            <Zap size={12} style={{ display: 'inline', marginRight: '4px' }} />
            Short (~180 mi)
          </button>
          <button 
            type="button" 
            className="btn-preset"
            onClick={() => loadPreset('Chicago, IL', 'Indianapolis, IN', 'Dallas, TX', 15)}
          >
            <Zap size={12} style={{ display: 'inline', marginRight: '4px' }} />
            Medium (~1,120 mi)
          </button>
          <button 
            type="button" 
            className="btn-preset"
            onClick={() => loadPreset('New York, NY', 'Atlanta, GA', 'Los Angeles, CA', 45)}
          >
            <Zap size={12} style={{ display: 'inline', marginRight: '4px' }} />
            Long (~2,800 mi)
          </button>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label" htmlFor="current_location">Current Location</label>
          <input
            id="current_location"
            type="text"
            className="form-input"
            placeholder="e.g. Chicago, IL"
            value={currentLocation}
            onChange={(e) => setCurrentLocation(e.target.value)}
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
            onChange={(e) => setPickupLocation(e.target.value)}
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
            onChange={(e) => setDropoffLocation(e.target.value)}
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
            onChange={(e) => setCurrentCycleUsed(e.target.value)}
            required
          />
        </div>

        <button type="submit" className="btn-submit" disabled={loading}>
          {loading ? (
            <span>Processing Route & HOS...</span>
          ) : (
            <>
              <Play size={18} />
              Calculate Route & ELD Logs
            </>
          )}
        </button>
      </form>
    </div>
  );
}
