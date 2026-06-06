import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Airport, Airplane } from '../models/airport.model';

@Injectable({ providedIn: 'root' })
export class AirportService {
  constructor(private http: HttpClient) {}

  /*getAirports(): Observable<Airport[]> {
    return this.http.get<Airport[]>('/airports');
  }

  getNearbyAirplanes(lat: number, lon: number): Observable<Airplane[]> {
    const params = new HttpParams()
      .set('lat', lat.toString())
      .set('lon', lon.toString());
    return this.http.get<Airplane[]>('/nearby-airplanes', { params });
  }*/

  // airport.service.ts
  private baseUrl = 'http://localhost:8000/api';

  getAirports(): Observable<Airport[]> {
    return this.http.get<Airport[]>(`${this.baseUrl}/fetch_airports`);
  }

  getNearbyAirplanes(lat: number, lon: number): Observable<Airplane[]> {
    const params = new HttpParams().set('lat', lat.toString()).set('lng', lon.toString());
    return this.http.get<Airplane[]>(`${this.baseUrl}/nearby_aircrafts`, { params });
  }
}
