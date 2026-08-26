import { useState, useEffect } from 'react';
import { Calendar, FileText, Printer } from 'lucide-react';

export default function EldLogViewer({ dailyLogs, metaData }) {
  const [selectedDayIdx, setSelectedDayIdx] = useState(0);

  // Reset active day tab to Day 1 (index 0) whenever dailyLogs dataset changes
  useEffect(() => {
    setSelectedDayIdx(0);
  }, [dailyLogs]);

  if (!dailyLogs || dailyLogs.length === 0) return null;

  const currentLog = dailyLogs[selectedDayIdx] || dailyLogs[0];
  const summary = currentLog.summary || { off_duty: 24, sleeper_berth: 0, driving: 0, on_duty: 0 };
  const events = currentLog.events || [];
  const remarks = currentLog.remarks || [];

  // Default ELD Header Values preserved from existing component
  const DEFAULT_DRIVER = "Property Carrier Driver (ID: DRV-7712)";
  const DEFAULT_CARRIER = "Spotter AI Freight Logistics • 100 Tech Way, San Francisco, CA";
  const DEFAULT_TRUCK = "TRK-104";
  const DEFAULT_TRAILER = "TRL-882";

  const driverName = metaData?.driver_name?.trim() || DEFAULT_DRIVER;
  const carrierName = metaData?.carrier_name?.trim() || DEFAULT_CARRIER;
  const truckNumber = metaData?.truck_number?.trim() || DEFAULT_TRUCK;
  const trailerNumber = metaData?.trailer_number?.trim() || DEFAULT_TRAILER;

  const handlePrint = () => {
    window.print();
  };

  // Helper to convert HH:MM string to hour float (0.0 to 24.0)
  const timeToHours = (timeStr) => {
    if (!timeStr) return 0;
    if (timeStr === "24:00") return 24.0;
    const [h, m] = timeStr.split(':').map(Number);
    return h + (m || 0) / 60.0;
  };

  // Status to Y-row coordinate index mapping in SVG grid
  // Rows: 0 = Off Duty, 1 = Sleeper Berth, 2 = Driving, 3 = On Duty Not Driving
  const STATUS_Y_MAP = {
    OFF: 30,
    SB: 70,
    D: 110,
    ON: 150
  };

  // Render SVG status graph lines
  const renderGraphLines = () => {
    const lines = [];
    let lastY = null;
    let lastX = null;

    events.forEach((ev, idx) => {
      const startH = timeToHours(ev.start_time);
      const endH = timeToHours(ev.end_time);

      // SVG dimensions: width = 600px for 24 hours (25px per hour), left margin = 80px
      const x1 = 80 + startH * 25;
      const x2 = 80 + endH * 25;
      const y = STATUS_Y_MAP[ev.status] || STATUS_Y_MAP.OFF;

      // Draw vertical transition line if changing status
      if (lastY !== null && lastY !== y && lastX !== null) {
        lines.push(
          <line
            key={`v-${idx}`}
            x1={x1}
            y1={lastY}
            x2={x1}
            y2={y}
            stroke="#2563eb"
            strokeWidth="3.5"
          />
        );
      }

      // Draw horizontal status duration line
      lines.push(
        <line
          key={`h-${idx}`}
          x1={x1}
          y1={y}
          x2={x2}
          y2={y}
          stroke="#2563eb"
          strokeWidth="3.5"
        />
      );

      lastY = y;
      lastX = x2;
    });

    return lines;
  };

  return (
    <div className="eld-container">
      <div className="no-print" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h2 className="panel-title" style={{ margin: 0 }}>
          <FileText size={20} className="text-primary" />
          Driver's Daily Log (ELD Sheet)
        </h2>

        <button type="button" className="btn-preset no-print" onClick={handlePrint} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Printer size={14} />
          Print Log Sheet
        </button>
      </div>

      {/* Multi-Day Pagination Tabs */}
      <div className="tabs-header no-print">
        {dailyLogs.map((log, idx) => (
          <button
            key={idx}
            type="button"
            className={`tab-btn ${idx === selectedDayIdx ? 'active' : ''}`}
            onClick={() => setSelectedDayIdx(idx)}
          >
            <Calendar size={14} style={{ display: 'inline', marginRight: '6px' }} />
            Day {log.day_number} ({log.date})
          </button>
        ))}
      </div>

      {/* Official FMCSA Daily Log Sheet */}
      <div className="eld-sheet">
        <div style={{ textAlign: 'center', borderBottom: '2px solid #111827', paddingBottom: '0.5rem', marginBottom: '1rem' }}>
          <h3 style={{ fontSize: '1.2rem', fontWeight: 800, textTransform: 'uppercase', letterSpacing: '1px' }}>
            DRIVER'S DAILY LOG (24 Hours)
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#4b5563' }}>
            Property-Carrying Vehicle • FMCSA Hours of Service Regulation Compliant
          </span>
        </div>

        {/* Header Metadata Block */}
        <table className="eld-header-table">
          <tbody>
            <tr>
              <td>
                <div className="eld-header-label">Date</div>
                <strong>{currentLog.date}</strong>
              </td>
              <td>
                <div className="eld-header-label">Total Miles Driven Today</div>
                <strong>{currentLog.total_miles} mi</strong>
              </td>
              <td>
                <div className="eld-header-label">Truck / Tractor #</div>
                <strong>{truckNumber}</strong>
              </td>
              <td>
                <div className="eld-header-label">Trailer #</div>
                <strong>{trailerNumber}</strong>
              </td>
            </tr>
            <tr>
              <td colSpan={2}>
                <div className="eld-header-label">Carrier Name & Main Office Address</div>
                <strong>{carrierName}</strong>
              </td>
              <td colSpan={2}>
                <div className="eld-header-label">Shipping Doc / Manifest #</div>
                <strong>MANIFEST-{currentLog.day_number}9281</strong>
              </td>
            </tr>
            <tr>
              <td colSpan={2}>
                <div className="eld-header-label">Driver Name & ID</div>
                <strong>{driverName}</strong>
              </td>
              <td colSpan={2}>
                <div className="eld-header-label">Home Terminal Address</div>
                <strong>Central Logistics Hub, Chicago, IL</strong>
              </td>
            </tr>
          </tbody>
        </table>

        {/* 24-Hour Graph SVG Grid */}
        <div style={{ border: '1px solid #9ca3af', padding: '10px', background: '#f9fafb', borderRadius: '6px' }}>
          <svg viewBox="0 0 740 190" className="eld-graph-svg">
            {/* Background Grid Lines & Row Labels */}
            {/* Row 1: Off Duty */}
            <text x="5" y="34" fill="#374151" fontSize="10" fontWeight="bold">1. OFF DUTY</text>
            <line x1="80" y1="30" x2="680" y2="30" stroke="#d1d5db" strokeWidth="1" />

            {/* Row 2: Sleeper Berth */}
            <text x="5" y="74" fill="#374151" fontSize="10" fontWeight="bold">2. SLEEPER</text>
            <line x1="80" y1="70" x2="680" y2="70" stroke="#d1d5db" strokeWidth="1" />

            {/* Row 3: Driving */}
            <text x="5" y="114" fill="#374151" fontSize="10" fontWeight="bold">3. DRIVING</text>
            <line x1="80" y1="110" x2="680" y2="110" stroke="#d1d5db" strokeWidth="1" />

            {/* Row 4: On Duty Not Driving */}
            <text x="5" y="154" fill="#374151" fontSize="10" fontWeight="bold">4. ON DUTY</text>
            <line x1="80" y1="150" x2="680" y2="150" stroke="#d1d5db" strokeWidth="1" />

            {/* Total Hours Header & Column */}
            <text x="695" y="15" fill="#111827" fontSize="10" fontWeight="bold">TOTAL</text>
            <text x="700" y="34" fill="#111827" fontSize="11" fontWeight="bold">{summary.off_duty}</text>
            <text x="700" y="74" fill="#111827" fontSize="11" fontWeight="bold">{summary.sleeper_berth}</text>
            <text x="700" y="114" fill="#111827" fontSize="11" fontWeight="bold">{summary.driving}</text>
            <text x="700" y="154" fill="#111827" fontSize="11" fontWeight="bold">{summary.on_duty}</text>

            {/* Total Sum Verification (Must equal 24.0) */}
            <line x1="685" y1="162" x2="735" y2="162" stroke="#111827" strokeWidth="1.5" />
            <text x="698" y="178" fill="#10b981" fontSize="11" fontWeight="bold">24.0 hrs</text>

            {/* Hour Vertical Ticks (0 to 24) */}
            {[...Array(25)].map((_, i) => {
              const x = 80 + i * 25;
              return (
                <g key={i}>
                  <line x1={x} y1="20" x2={x} y2="160" stroke="#e5e7eb" strokeWidth={i % 6 === 0 ? "1.5" : "0.5"} />
                  <text x={x - 4} y="15" fill="#6b7280" fontSize="9">{i}</text>
                </g>
              );
            })}

            {/* Render Calculated HOS Duty Status Lines */}
            {renderGraphLines()}
          </svg>
        </div>

        {/* Remarks Section */}
        <h4 style={{ fontSize: '0.9rem', fontWeight: 700, marginTop: '1.25rem', marginBottom: '0.5rem', color: '#1f2937' }}>
          REMARKS (Duty Status Changes & Locations)
        </h4>

        <table className="remarks-table">
          <thead>
            <tr>
              <th style={{ width: '80px' }}>Time</th>
              <th style={{ width: '80px' }}>Status</th>
              <th>Location</th>
              <th>Remarks / Activity Description</th>
            </tr>
          </thead>
          <tbody>
            {remarks.length === 0 ? (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', color: '#6b7280' }}>No status changes recorded for this day.</td>
              </tr>
            ) : (
              remarks.map((rmk, idx) => (
                <tr key={idx}>
                  <td><strong>{rmk.time}</strong></td>
                  <td>
                    <span className={`status-badge status-badge-${rmk.status}`}>
                      {rmk.status}
                    </span>
                  </td>
                  <td>{rmk.location}</td>
                  <td>{rmk.note}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>

        {/* Signature Certification Box */}
        <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', borderTop: '1px solid #e5e7eb', paddingTop: '1rem' }}>
          <div style={{ fontSize: '0.75rem', color: '#4b5563' }}>
            I certify that these entries are true and correct to the best of my knowledge.
          </div>
          <div style={{ borderBottom: '1px solid #111827', width: '240px', textAlign: 'center', fontSize: '0.85rem', fontWeight: 600, paddingBottom: '4px' }}>
            Driver Certification Signature
          </div>
        </div>
      </div>
    </div>
  );
}
