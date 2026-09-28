/**
 * Geolocation & Routing Utilities for Stampu
 */

export interface GeoCoordinates {
  latitude: number;
  longitude: number;
}

/**
 * Calculates Great-Circle distance between two points on Earth using Haversine formula
 */
export function calculateDistanceKm(
  lat1: number,
  lon1: number,
  lat2: number,
  lon2: number
): number {
  const R = 6371; // Earth's mean radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

/**
 * Formats distance into friendly meters or kilometers
 */
export function formatDistance(km: number): string {
  if (km < 1) {
    const meters = Math.round(km * 1000);
    return `${meters} m`;
  }
  if (km < 10) {
    return `${km.toFixed(1)} km`;
  }
  return `${Math.round(km)} km`;
}

/**
 * Returns navigation URL in Google Maps
 */
export function getGoogleMapsUrl(lat: number, lon: number, destinationName?: string): string {
  const encodedName = destinationName ? encodeURIComponent(destinationName) : '';
  return `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}&destination_name=${encodedName}`;
}

/**
 * Opens navigation in Google Maps app or web
 */
export function openInGoogleMaps(lat: number, lon: number, destinationName?: string): string {
  const url = getGoogleMapsUrl(lat, lon, destinationName);
  if (typeof window !== 'undefined' && typeof window.open === 'function') {
    window.open(url, '_blank', 'noopener,noreferrer');
  }
  return url;
}
