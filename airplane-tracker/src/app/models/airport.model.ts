export interface Airport {
  id: string | number;
  name: string;
  iata?: string;
  icao?: string;
  lat: number;
  lon: number;
  city?: string;
  country?: string;
}

export interface Airplane {
  callsign: string;
  latitude: number;
  longitude: number;
  velocity: number;
  altitude: number;
}

export interface AirplaneResponse {
  items: Airplane[];
  update: boolean;
}

export type AltitudeCategory = 'low' | 'mid' | 'high';

export function getAltitudeCategory(altitude: number): AltitudeCategory {
  if (altitude < 3000) return 'low';
  if (altitude <= 18000) return 'mid';
  return 'high';
}
