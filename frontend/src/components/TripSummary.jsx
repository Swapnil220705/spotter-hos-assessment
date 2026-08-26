import { Route, Clock, Briefcase, Moon, Calendar, AlertTriangle, Gauge } from 'lucide-react';

const METRIC_CONFIG = [
  {
    key: 'total_distance_miles',
    label: 'Total Distance',
    icon: Route,
    color: '#3b82f6',
    format: (v) => typeof v === 'number'
      ? v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 1 }) + ' mi'
      : v + ' mi',
  },
  {
    key: 'total_driving_hours',
    label: 'Driving Time',
    icon: Gauge,
    color: '#10b981',
    format: (v) => `${v}h`,
  },
  {
    key: 'total_on_duty_hours',
    label: 'On-Duty Work',
    icon: Briefcase,
    color: '#f59e0b',
    format: (v) => `${v}h`,
  },
  {
    key: 'total_rest_hours',
    label: 'Rest / Breaks',
    icon: Moon,
    color: '#8b5cf6',
    format: (v) => `${v}h`,
  },
  {
    key: 'total_trip_hours',
    label: 'Elapsed Time',
    icon: Clock,
    color: '#6366f1',
    format: (v) => `${v}h`,
  },
  {
    key: 'total_days',
    label: 'Daily Logs',
    icon: Calendar,
    color: '#ec4899',
    format: (v) => `${v} ${v === 1 ? 'day' : 'days'}`,
  },
];

export default function TripSummary({ summary }) {
  if (!summary) return null;

  // HOS compliance check: warn if approaching 70h cycle
  const showCycleWarning = (summary.total_driving_hours || 0) >= 10;

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      {/* Summary Section Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: '0.5rem',
        marginBottom: '0.875rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <Route size={18} style={{ color: 'var(--primary)' }} />
          <span style={{ fontWeight: 600, fontSize: '1rem', color: '#fff' }}>Trip Overview</span>
        </div>
        {showCycleWarning && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: '5px',
            background: 'rgba(245,158,11,0.15)',
            border: '1px solid rgba(245,158,11,0.4)',
            borderRadius: '6px',
            padding: '3px 10px',
            fontSize: '0.75rem',
            fontWeight: 600,
            color: '#fbbf24',
          }}>
            <AlertTriangle size={12} />
            Multi-segment trip
          </div>
        )}
      </div>

      {/* Metric Cards Grid */}
      <div className="metrics-grid">
        {METRIC_CONFIG.map(({ key, label, icon: Icon, color, format }) => {
          const value = summary[key];
          if (value === undefined || value === null) return null;
          return (
            <div
              key={key}
              className="metric-card"
              style={{ borderTop: `3px solid ${color}`, position: 'relative', overflow: 'hidden' }}
            >
              {/* Subtle glow backdrop */}
              <div style={{
                position: 'absolute', top: 0, left: 0, right: 0, height: '40px',
                background: `linear-gradient(180deg, ${color}18 0%, transparent 100%)`,
                pointerEvents: 'none',
              }} />
              <div style={{ position: 'relative' }}>
                <Icon size={16} style={{ color, marginBottom: '6px' }} />
                <div className="metric-value" style={{ color }}>
                  {format(value)}
                </div>
                <div className="metric-label">{label}</div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
