import { useEffect } from 'react';
import { MapContainer, TileLayer, Polyline, Marker, Popup, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

// Custom Marker DivIcons for distinct HOS Waypoint markers
function createCustomIcon(color, letter) {
  return L.divIcon({
    className: 'custom-map-marker',
    html: `<div style="
      background-color: ${color};
      color: white;
      width: 28px;
      height: 28px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: bold;
      font-size: 12px;
      border: 2px solid white;
      box-shadow: 0 3px 8px rgba(0,0,0,0.4);
    ">${letter}</div>`,
    iconSize: [28, 28],
    iconAnchor: [14, 14],
  });
}

const WAYPOINT_ICONS = {
  ORIGIN: createCustomIcon('#3b82f6', 'O'),
  PICKUP: createCustomIcon('#10b981', 'P'),
  DROPOFF: createCustomIcon('#ef4444', 'D'),
  FUEL: createCustomIcon('#f59e0b', 'F'),
  REST_30M: createCustomIcon('#8b5cf6', 'B'),
  REST_10H: createCustomIcon('#6366f1', 'R'),
  RESTART_34H: createCustomIcon('#ec4899', 'S'),
};

// Helper component to auto-fit map bounds to the route
function MapBoundsUpdater({ coordinates }) {
  const map = useMap();
  
  useEffect(() => {
    if (coordinates && coordinates.length > 0) {
      const bounds = L.latLngBounds(coordinates);
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [coordinates, map]);

  return null;
}

export default function RouteMap({ route }) {
  if (!route || !route.coordinates || route.coordinates.length === 0) {
    // Default US view when no route is loaded
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
    <div className="map-wrapper">
      <MapContainer center={initialCenter} zoom={6} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        
        <Polyline positions={coordinates} color="#3b82f6" weight={5} opacity={0.8} />
        
        {waypoints.map((wp, idx) => (
          <Marker
            key={idx}
            position={[wp.lat, wp.lng]}
            icon={WAYPOINT_ICONS[wp.type] || WAYPOINT_ICONS.ORIGIN}
          >
            <Popup>
              <div style={{ padding: '4px' }}>
                <strong style={{ fontSize: '13px', color: '#111' }}>{wp.type} - {wp.name}</strong>
                {wp.time && <div style={{ fontSize: '11px', color: '#666', marginTop: '4px' }}>Time: {wp.time}</div>}
              </div>
            </Popup>
          </Marker>
        ))}

        <MapBoundsUpdater coordinates={coordinates} />
      </MapContainer>
    </div>
  );
}
