import { useState, useRef, useEffect, useCallback } from 'react';
import { Navigation, Play, Zap, AlertCircle, MapPin, Loader } from 'lucide-react';
import { fetchLocationSuggestions } from '../services/api';

// ---------------------------------------------------------------------------
// LocationInput — a single location field with debounced autocomplete
// ---------------------------------------------------------------------------
function LocationInput({ id, label, placeholder, value, onChange, disabled }) {
  const [suggestions, setSuggestions] = useState([]);
  const [suggestLoading, setSuggestLoading] = useState(false);
  const [suggestError, setSuggestError] = useState(false);
  const [open, setOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);

  const abortRef = useRef(null);
  const debounceRef = useRef(null);
  const containerRef = useRef(null);
  const listboxId = `${id}-listbox`;

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(e) {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const fetchSuggestions = useCallback((query) => {
    // Cancel any in-flight request
    if (abortRef.current) abortRef.current.abort();

    if (!query || query.trim().length < 3) {
      setSuggestions([]);
      setOpen(false);
      setSuggestLoading(false);
      return;
    }

    abortRef.current = new AbortController();
    setSuggestLoading(true);
    setSuggestError(false);

    fetchLocationSuggestions(query.trim(), abortRef.current.signal)
      .then((results) => {
        setSuggestions(results);
        setActiveIdx(-1);
        setOpen(true);
        setSuggestLoading(false);
      })
      .catch((err) => {
        // AbortError = stale request, ignore silently
        if (err && err.name === 'AbortError') return;
        // Genuine failure: allow manual typing, show subtle indicator
        setSuggestError(true);
        setSuggestions([]);
        setOpen(false);
        setSuggestLoading(false);
      });
  }, []);

  const handleChange = (e) => {
    const newVal = e.target.value;
    onChange(newVal);
    setSuggestError(false);

    // Clear previous debounce timer
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(newVal), 350);
  };

  const handleSelect = (suggestion) => {
    // Use display_name for geocoding accuracy; short_name for readability
    onChange(suggestion.short_name || suggestion.display_name);
    setSuggestions([]);
    setOpen(false);
    setActiveIdx(-1);
    if (abortRef.current) abortRef.current.abort();
    clearTimeout(debounceRef.current);
  };

  const handleKeyDown = (e) => {
    if (!open || suggestions.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter' && activeIdx >= 0) {
      e.preventDefault();
      handleSelect(suggestions[activeIdx]);
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActiveIdx(-1);
    }
  };

  const handleBlur = () => {
    // Small delay so click on suggestion registers before blur closes the list
    setTimeout(() => {
      if (containerRef.current && !containerRef.current.contains(document.activeElement)) {
        setOpen(false);
      }
    }, 120);
  };

  const showDropdown = open && !disabled && (
    suggestLoading || suggestions.length > 0 || suggestError
  );

  return (
    <div className="form-group location-input-wrapper" ref={containerRef}>
      <label className="form-label" htmlFor={id}>{label}</label>
      <div style={{ position: 'relative' }}>
        <input
          id={id}
          type="text"
          className="form-input"
          placeholder={placeholder}
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onBlur={handleBlur}
          disabled={disabled}
          required
          autoComplete="off"
          aria-autocomplete="list"
          aria-expanded={showDropdown ? 'true' : 'false'}
          aria-controls={showDropdown ? listboxId : undefined}
          aria-activedescendant={activeIdx >= 0 ? `${listboxId}-opt-${activeIdx}` : undefined}
        />
        {suggestLoading && (
          <span className="suggest-spinner" aria-hidden="true">
            <Loader size={14} />
          </span>
        )}
      </div>

      {showDropdown && (
        <ul
          id={listboxId}
          className="suggest-dropdown"
          role="listbox"
          aria-label={`${label} suggestions`}
        >
          {suggestLoading && (
            <li className="suggest-item suggest-meta" role="option" aria-selected="false">
              <Loader size={12} style={{ display: 'inline', marginRight: 6 }} />
              Searching locations…
            </li>
          )}
          {!suggestLoading && suggestions.length === 0 && !suggestError && (
            <li className="suggest-item suggest-meta" role="option" aria-selected="false">
              No matching locations found
            </li>
          )}
          {!suggestLoading && suggestError && (
            <li className="suggest-item suggest-meta" role="option" aria-selected="false">
              Suggestions unavailable — type location manually
            </li>
          )}
          {!suggestLoading && suggestions.map((s, idx) => (
            <li
              key={idx}
              id={`${listboxId}-opt-${idx}`}
              className={`suggest-item${activeIdx === idx ? ' suggest-active' : ''}`}
              role="option"
              aria-selected={activeIdx === idx ? 'true' : 'false'}
              onMouseDown={(e) => { e.preventDefault(); handleSelect(s); }}
              onMouseEnter={() => setActiveIdx(idx)}
            >
              <MapPin size={12} className="suggest-icon" aria-hidden="true" />
              <span className="suggest-text">
                <span className="suggest-short">{s.short_name}</span>
                {s.display_name !== s.short_name && (
                  <span className="suggest-full">{s.display_name}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// TripForm — main form; all existing behaviour preserved
// ---------------------------------------------------------------------------
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
        <LocationInput
          id="current_location"
          label="Current Location"
          placeholder="e.g. Chicago, IL"
          value={currentLocation}
          onChange={(v) => { setValidationError(null); setCurrentLocation(v); }}
          disabled={loading}
        />

        <LocationInput
          id="pickup_location"
          label="Pickup Location"
          placeholder="e.g. Indianapolis, IN"
          value={pickupLocation}
          onChange={(v) => { setValidationError(null); setPickupLocation(v); }}
          disabled={loading}
        />

        <LocationInput
          id="dropoff_location"
          label="Dropoff Location"
          placeholder="e.g. Dallas, TX"
          value={dropoffLocation}
          onChange={(v) => { setValidationError(null); setDropoffLocation(v); }}
          disabled={loading}
        />

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
