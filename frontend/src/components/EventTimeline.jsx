import { MapPin, Truck, Package, Fuel, Coffee, Moon, RefreshCw, Flag } from 'lucide-react';

const EVENT_CONFIG = {
  ORIGIN:      { icon: Truck,      label: 'Trip Start',    color: '#3b82f6', bg: 'rgba(59,130,246,0.12)',  badge: 'START' },
  PICKUP:      { icon: Package,    label: 'Pickup',        color: '#10b981', bg: 'rgba(16,185,129,0.12)',  badge: 'PICKUP' },
  DROPOFF:     { icon: Flag,       label: 'Dropoff',       color: '#ef4444', bg: 'rgba(239,68,68,0.12)',   badge: 'DROPOFF' },
  FUEL:        { icon: Fuel,       label: 'Fuel Stop',     color: '#f59e0b', bg: 'rgba(245,158,11,0.12)', badge: 'FUEL' },
  REST_30M:    { icon: Coffee,     label: '30-Min Break',  color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)', badge: '30 MIN' },
  REST_10H:    { icon: Moon,       label: '10-Hr Rest',    color: '#6366f1', bg: 'rgba(99,102,241,0.12)',  badge: '10 HR' },
  RESTART_34H: { icon: RefreshCw,  label: '34-Hr Restart', color: '#ec4899', bg: 'rgba(236,72,153,0.12)',  badge: '34 HR' },
};

export default function EventTimeline({ waypoints }) {
  if (!waypoints || waypoints.length === 0) return null;

  return (
    <div style={{ position: 'relative' }}>
      {/* Vertical connector line */}
      <div style={{
        position: 'absolute',
        left: '19px',
        top: '20px',
        bottom: '20px',
        width: '2px',
        background: 'linear-gradient(180deg, rgba(59,130,246,0.5) 0%, rgba(99,102,241,0.2) 100%)',
        borderRadius: '2px',
      }} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', paddingBottom: '4px' }}>
        {waypoints.map((wp, idx) => {
          const cfg = EVENT_CONFIG[wp.type] || {
            icon: MapPin, label: wp.type, color: '#6b7280', bg: 'rgba(107,114,128,0.1)', badge: wp.type,
          };
          const Icon = cfg.icon;

          return (
            <div
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '12px',
                position: 'relative',
                zIndex: 1,
              }}
            >
              {/* Event icon dot */}
              <div style={{
                width: '38px',
                height: '38px',
                flexShrink: 0,
                borderRadius: '50%',
                background: cfg.bg,
                border: `2px solid ${cfg.color}55`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: `0 0 8px ${cfg.color}33`,
              }}>
                <Icon size={16} style={{ color: cfg.color }} />
              </div>

              {/* Event content card */}
              <div style={{
                flex: 1,
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '8px',
                padding: '8px 12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                gap: '8px',
                flexWrap: 'wrap',
                minWidth: 0,
              }}>
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '2px' }}>
                    <span style={{
                      background: cfg.color + '22',
                      color: cfg.color,
                      border: `1px solid ${cfg.color}44`,
                      borderRadius: '4px',
                      padding: '1px 6px',
                      fontSize: '9px',
                      fontWeight: 700,
                      textTransform: 'uppercase',
                      letterSpacing: '0.6px',
                      flexShrink: 0,
                    }}>{cfg.badge}</span>
                    <span style={{
                      fontWeight: 600,
                      fontSize: '0.82rem',
                      color: '#e5e7eb',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>{wp.name}</span>
                  </div>
                  {wp.time && (
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
                      ⏱ {wp.time}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
