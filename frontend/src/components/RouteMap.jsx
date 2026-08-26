import { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Custom Marker DivIcons for distinct HOS Waypoint markers
function createCustomIcon(bg, border, letter, shape = 'circle') {
  const borderRadius = shape === 'diamond' ? '4px' : '50%';
  const transform = shape === 'diamond' ? 'rotate(45deg)' : 'none';
  const innerTransform = shape === 'diamond' ? 'rotate(-45deg)' : 'none';
  return L.divIcon({
    className: 'custom-map-marker',
    html: `<div style="
      background: ${bg};
      width: 32px;
      height: 32px;
      border-radius: ${borderRadius};
      transform: ${transform};
      display: flex;
      align-items: center;
      justify-content: center;
      border: 2.5px solid ${border};
      box-shadow: 0 3px 10px rgba(0,0,0,0.5), 0 0 0 3px rgba(0,0,0,0.2);
    "><span style="
      transform: ${innerTransform};
      color: white;
      font-weight: 800;
      font-size: 13px;
      font-family: Inter, system-ui, sans-serif;
      line-height: 1;
    ">${letter}</span></div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });
}

const WAYPOINT_ICONS = {
  ORIGIN:      createCustomIcon('linear-gradient(135deg,#2563eb,#3b82f6)', '#93c5fd', 'A'),
  PICKUP:      createCustomIcon('linear-gradient(135deg,#059669,#10b981)', '#6ee7b7', 'P'),
  DROPOFF:     createCustomIcon('linear-gradient(135deg,#dc2626,#ef4444)', '#fca5a5', 'D', 'diamond'),
  FUEL:        createCustomIcon('linear-gradient(135deg,#d97706,#f59e0b)', '#fcd34d', 'F'),
  REST_30M:    createCustomIcon('linear-gradient(135deg,#7c3aed,#8b5cf6)', '#c4b5fd', '30'),
  REST_10H:    createCustomIcon('linear-gradient(135deg,#4338ca,#6366f1)', '#a5b4fc', '10'),
  RESTART_34H: createCustomIcon('linear-gradient(135deg,#be185d,#ec4899)', '#fbcfe8', 'R'),
};

const WAYPOINT_LABELS = {
  ORIGIN:      { label: 'Origin',         color: '#3b82f6' },
  PICKUP:      { label: 'Pickup',          color: '#10b981' },
  DROPOFF:     { label: 'Dropoff',         color: '#ef4444' },
  FUEL:        { label: 'Fuel Stop',       color: '#f59e0b' },
  REST_30M:    { label: '30-Min Break',    color: '#8b5cf6' },
  REST_10H:    { label: '10-Hr Rest',      color: '#6366f1' },
  RESTART_34H: { label: '34-Hr Restart',   color: '#ec4899' },
};

// Helper component to auto-fit map bounds to the route
function MapBoundsUpdater({ coordinates }) {
  const map = useMap();
  useEffect(() => {
    if (coordinates && coordinates.length > 0) {
      const bounds = L.latLngBounds(coordinates);
      map.fitBounds(bounds, { padding: [50, 50] });
    }
  }, [coordinates, map]);
  return null;
}

// Map legend overlay component
function MapLegend({ waypoints }) {
  const usedTypes = [...new Set((waypoints || []).map(w => w.type))];
  const legendItems = usedTypes
    .filter(t => WAYPOINT_LABELS[t])
    .map(t => ({ type: t, ...WAYPOINT_LABELS[t] }));

  if (legendItems.length === 0) return null;

  return (
    <div style={{
      position: 'absolute',
      bottom: '12px',
      right: '10px',
      zIndex: 1000,
      background: 'rgba(10,13,20,0.92)',
      backdropFilter: 'blur(8px)',
      border: '1px solid rgba(255,255,255,0.12)',
      borderRadius: '10px',
      padding: '10px 14px',
      fontSize: '11px',
      color: '#f3f4f6',
      pointerEvents: 'none',
      minWidth: '130px',
    }}>
      <div style={{ fontWeight: 700, fontSize: '10px', textTransform: 'uppercase', letterSpacing: '0.8px', color: '#9ca3af', marginBottom: '8px' }}>
        Waypoints
      </div>
      {legendItems.map(item => (
        <div key={item.type} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '5px' }}>
          <div style={{
            width: '10px', height: '10px', borderRadius: '50%',
            background: item.color, flexShrink: 0,
            boxShadow: `0 0 4px ${item.color}66`
          }} />
          <span style={{ color: '#e5e7eb' }}>{item.label}</span>
        </div>
      ))}
    </div>
  );
}

export default function RouteMap({ route }) {
  if (!route || !route.coordinates || route.coordinates.length === 0) {
    return (
      <div className="map-wrapper">
        <MapContainer center={[39.8283, -98.5795]} zoom={4} style={{ height: '100%', width: '100%' }}>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
        </MapContainer>
      </div>
    );
  }

  const coordinates = route.coordinates;
  const waypoints = route.waypoints || [];
  const initialCenter = coordinates[0] || [39.8283, -98.5795];

  return (
    <div className="map-wrapper" style={{ position: 'relative' }}>
      <MapContainer center={initialCenter} zoom={6} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Route shadow for depth */}
        <Polyline positions={coordinates} color="#1e3a5f" weight={9} opacity={0.4} />
        <Polyline positions={coordinates} color="#3b82f6" weight={5} opacity={0.9} />

        {waypoints.map((wp, idx) => {
          const icon = WAYPOINT_ICONS[wp.type] || WAYPOINT_ICONS.ORIGIN;
          const meta = WAYPOINT_LABELS[wp.type] || { label: wp.type, color: '#6b7280' };
          return (
            <Marker key={idx} position={[wp.lat, wp.lng]} icon={icon}>
              <Popup>
                <div style={{ padding: '6px 2px', minWidth: '160px' }}>
                  <div style={{
                    display: 'inline-block',
                    background: meta.color + '22',
                    color: meta.color,
                    border: `1px solid ${meta.color}55`,
                    borderRadius: '4px',
                    padding: '2px 8px',
                    fontSize: '10px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                    marginBottom: '6px',
                  }}>{meta.label}</div>
                  <div style={{ fontWeight: 700, fontSize: '13px', color: '#111', marginBottom: '3px' }}>
                    {wp.name}
                  </div>
                  {wp.time && (
                    <div style={{ fontSize: '11px', color: '#555' }}>
                      ⏱ {wp.time}
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        <MapBoundsUpdater coordinates={coordinates} />
      </MapContainer>

      <MapLegend waypoints={waypoints} />
    </div>
  );
}
