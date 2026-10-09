'use client';

import { useEffect, useMemo, useRef } from 'react';

interface EmergencyMapProps {
  userLocation?: { lat: number; lng: number };
  facilityLocation: { lat: number; lng: number };
  facilityName: string;
}

declare global {
  interface Window {
    L?: any;
  }
}

const LEAFLET_CSS_ID = 'leaflet-css-cdn';
const LEAFLET_SCRIPT_ID = 'leaflet-js-cdn';

function ensureLeafletAssetsLoaded(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.L) {
      resolve();
      return;
    }

    if (!document.getElementById(LEAFLET_CSS_ID)) {
      const css = document.createElement('link');
      css.id = LEAFLET_CSS_ID;
      css.rel = 'stylesheet';
      css.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
      css.integrity = 'sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=';
      css.crossOrigin = '';
      document.head.appendChild(css);
    }

    const existingScript = document.getElementById(LEAFLET_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true });
      existingScript.addEventListener('error', () => reject(new Error('Failed to load Leaflet script')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = LEAFLET_SCRIPT_ID;
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.integrity = 'sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=';
    script.crossOrigin = '';
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Failed to load Leaflet script'));
    document.body.appendChild(script);
  });
}

export function EmergencyMap({ userLocation, facilityLocation, facilityName }: EmergencyMapProps) {
  const mapRef = useRef<HTMLDivElement | null>(null);
  const leafletMapRef = useRef<any>(null);
  const fallbackRef = useRef<HTMLDivElement | null>(null);

  const routeBounds = useMemo(() => {
    const points = [facilityLocation];
    if (userLocation) points.push(userLocation);
    return points;
  }, [facilityLocation, userLocation]);

  useEffect(() => {
    let cancelled = false;

    const setupMap = async () => {
      await ensureLeafletAssetsLoaded();
      if (cancelled || !mapRef.current || !window.L) return;

      const L = window.L;
      const userIcon = L.icon({
        iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41],
      });
      const facilityIcon = L.icon({
        iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png',
        shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41],
      });

      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }

      const map = L.map(mapRef.current, { zoomControl: true });
      leafletMapRef.current = map;

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(map);

      L.marker([facilityLocation.lat, facilityLocation.lng], { icon: facilityIcon })
        .addTo(map)
        .bindPopup(`<strong>Nearest Facility</strong><br/>${facilityName}`);

      if (userLocation) {
        L.marker([userLocation.lat, userLocation.lng], { icon: userIcon })
          .addTo(map)
          .bindPopup('<strong>Your Location</strong>');

        L.polyline(
          [
            [userLocation.lat, userLocation.lng],
            [facilityLocation.lat, facilityLocation.lng],
          ],
          { color: '#dc2626', weight: 4, opacity: 0.75 },
        ).addTo(map);
      }

      const bounds = L.latLngBounds(routeBounds.map((point) => [point.lat, point.lng]));
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [24, 24] });
      } else {
        map.setView([facilityLocation.lat, facilityLocation.lng], 13);
      }
    };

    void setupMap().catch(() => {
      if (fallbackRef.current) {
        fallbackRef.current.style.display = 'flex';
      }
    });

    return () => {
      cancelled = true;
      if (leafletMapRef.current) {
        leafletMapRef.current.remove();
        leafletMapRef.current = null;
      }
    };
  }, [facilityLocation, facilityName, routeBounds, userLocation]);

  return (
    <div className="relative w-full h-56" aria-label="Emergency map with user and facility markers">
      <div ref={mapRef} className="absolute inset-0" />
      <div
        ref={fallbackRef}
        className="absolute inset-0 hidden items-center justify-center bg-red-50 text-red-800 text-sm px-4 text-center"
      >
        Map preview unavailable. Use the Open Maps button for navigation to {facilityName}.
      </div>
    </div>
  );
}
