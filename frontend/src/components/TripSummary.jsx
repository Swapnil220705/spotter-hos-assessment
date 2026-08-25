export default function TripSummary({ summary }) {
  if (!summary) return null;

  const formattedMiles = typeof summary.total_distance_miles === 'number'
    ? summary.total_distance_miles.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 1 })
    : summary.total_distance_miles;

  return (
    <div className="metrics-grid">
      <div className="metric-card">
        <div className="metric-value">{formattedMiles}</div>
        <div className="metric-label">Total Miles</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{summary.total_driving_hours}h</div>
        <div className="metric-label">Driving Time</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{summary.total_on_duty_hours}h</div>
        <div className="metric-label">On-Duty Work</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{summary.total_rest_hours}h</div>
        <div className="metric-label">Rest / Breaks</div>
      </div>
      <div className="metric-card">
        <div className="metric-value">{summary.total_days}</div>
        <div className="metric-label">Daily Logs</div>
      </div>
    </div>
  );
}
