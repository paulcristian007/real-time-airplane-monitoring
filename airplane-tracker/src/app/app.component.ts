import {
  Component,
  OnDestroy,
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  signal,
  computed,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription, interval, switchMap, catchError, of } from 'rxjs';
import { AirportService } from './services/airport.service';
import {Airport, Airplane, getAltitudeCategory, AirplaneResponse} from './models/airport.model';
import {resolve} from "@angular/compiler-cli";
import {HttpResponse} from "@angular/common/http";

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AppComponent implements OnDestroy {
  // Airport search state
  airports: Airport[] = [];
  filteredAirports: Airport[] = [];
  searchQuery = '';
  selectedAirport: Airport | null = null;
  dropdownOpen = false;
  loadingAirports = false;
  airportsError = false;

  // Monitoring state
  isMonitoring = false;
  airplanes: Airplane[] = [];
  loadingPlanes = false;
  monitorError = false;
  lastUpdated: Date | null = null;

  isBackupData = false;
  pollCount = 0;

  private monitorTimeout: any;

  private monitorSub?: Subscription;

  constructor(
    private airportService: AirportService,
    private cdr: ChangeDetectorRef
  ) {
    this.loadAirports();
  }

  // ── Airports ────────────────────────────────────────────────────────────────

  loadAirports(): void {
    this.loadingAirports = true;
    this.airportsError = false;
    this.airportService.getAirports().subscribe({
      next: (data: any) => {
        this.airports = data.items;
        this.filteredAirports = data.items;
        this.loadingAirports = false;
        this.cdr.markForCheck();
      },
      error: () => {
        this.loadingAirports = false;
        this.airportsError = true;
        this.cdr.markForCheck();
      },
    });
  }

  onSearchInput(): void {
    const q = this.searchQuery.toLowerCase().trim();
    this.filteredAirports = q
      ? this.airports.filter(
          (a) =>
            a.name.toLowerCase().includes(q) ||
            a.iata?.toLowerCase().includes(q) ||
            a.icao?.toLowerCase().includes(q) ||
            a.city?.toLowerCase().includes(q)
        )
      : this.airports;
    this.dropdownOpen = true;
    this.selectedAirport = null;
  }

  selectAirport(airport: Airport): void {
    this.selectedAirport = airport;
    this.searchQuery = `${airport.name}${airport.iata ? ' (' + airport.iata + ')' : ''}`;
    this.dropdownOpen = false;
  }

  openDropdown(): void {
    this.dropdownOpen = true;
    this.filteredAirports = this.searchQuery
      ? this.filteredAirports
      : this.airports;
  }

  closeDropdown(): void {
    // Delay so click on item registers first
    setTimeout(() => {
      this.dropdownOpen = false;
      this.cdr.markForCheck();
    }, 150);
  }

  // ── Monitoring ──────────────────────────────────────────────────────────────

  /*startMonitoring(): void {
  if (!this.selectedAirport || this.isMonitoring) return;
  this.isMonitoring = true;
  this.monitorError = false;

  const poll = () => {
    this.loadingPlanes = true;
    this.airportService
      .getNearbyAirplanes(this.selectedAirport!.lat, this.selectedAirport!.lon)
      .pipe(catchError(() => {
        this.monitorError = true;
        this.airplanes = [];
        this.cdr.markForCheck();
        return of(null);
      }))
      .subscribe((planes) => {
        if (planes !== null) {
          this.airplanes = this.sortByAltitude(planes);
          this.monitorError = false;
          this.lastUpdated = new Date();
          this.pollCount++;
        }
        this.loadingPlanes = false;
        this.cdr.markForCheck();
        if (this.isMonitoring) {
          const delay = this.monitorError ? 1000 : 5000; // 10s on error, 2s normal
          this.monitorTimeout = setTimeout(poll, delay);
        }
      });
  };

  poll();
}

  stopMonitoring(): void {
    this.isMonitoring = false;
    clearTimeout(this.monitorTimeout);
    this.loadingPlanes = false;
    this.cdr.markForCheck();
  }*/

  /*startMonitoring(): void {
  if (!this.selectedAirport || this.isMonitoring) return;
  this.isMonitoring = true;
  this.monitorError = false;
  this.pollCount = 0;

  this.monitorSub = interval(5000)
    .pipe(
      switchMap(() => {
        this.loadingPlanes = true;
        this.cdr.markForCheck();
        return this.airportService
          .getNearbyAirplanes(this.selectedAirport!.lat, this.selectedAirport!.lon)
          .pipe(catchError(() => {
            this.monitorError = true;
            this.airplanes = [];
            return of(null);
          }));
      })
    )
    .subscribe({
      next: (response) => {
        if (!response) return;
        const planes = response.body ?? [];
        this.airplanes = this.sortByAltitude(planes);
        this.loadingPlanes = false;
        this.lastUpdated = new Date();
        this.pollCount++;
        if (this.airplanes.length > 0) {
          this.monitorError = false;
        }
        this.cdr.markForCheck();
      },
    });

  // Immediately fire first request
  this.loadingPlanes = true;
  this.airportService
    .getNearbyAirplanes(this.selectedAirport.lat, this.selectedAirport.lon)
    .pipe(catchError(() => {
      this.monitorError = true;
      this.airplanes = [];
      return of(null);
    }))
    .subscribe((response) => {
      if (!response) return;
      const planes = response.body ?? [];
      this.airplanes = this.sortByAltitude(planes);
      this.loadingPlanes = false;
      this.lastUpdated = new Date();
      this.pollCount++;
      this.cdr.markForCheck();
    });
}*/

  startMonitoring(): void {
    if (!this.selectedAirport || this.isMonitoring) return;
    this.isMonitoring = true;
    this.monitorError = false;
    this.pollCount = 0;

    this.monitorSub = interval(5000)
      .pipe(
        switchMap(() => {
          this.loadingPlanes = true;
          this.cdr.markForCheck();
          return this.airportService
            .getNearbyAirplanes(
              this.selectedAirport!.lat,
              this.selectedAirport!.lon
            )
            .pipe(catchError(() => {
              this.monitorError = true;
              return of({"items": [], "update": false});
            }));
        })
      )
      .subscribe({
        next: (response) => {
          const finalresponse = response as AirplaneResponse;
          this.airplanes = this.sortByAltitude(finalresponse.items);
          this.isBackupData = finalresponse.update;
          this.loadingPlanes = false;
          this.lastUpdated = new Date();
          this.pollCount++;
          if (this.airplanes.length > 0) {
            this.monitorError = false;
          }
          this.cdr.markForCheck();
        },
      });

    // Immediately fire first request
    this.loadingPlanes = true;
    this.airportService
      .getNearbyAirplanes(this.selectedAirport.lat, this.selectedAirport.lon)
      .pipe(catchError(() => { this.monitorError = true; return of([]); }))
      .subscribe((response) => {
        const finalresponse = response as AirplaneResponse;
        this.airplanes = this.sortByAltitude(finalresponse.items);
        this.isBackupData = finalresponse.update;
        this.loadingPlanes = false;
        this.lastUpdated = new Date();
        this.pollCount++;
        this.cdr.markForCheck();
      });
  }

  stopMonitoring(): void {
    this.monitorSub?.unsubscribe();
    this.isMonitoring = false;
    this.loadingPlanes = false;
    this.cdr.markForCheck();
  }

  private sortByAltitude(planes: Airplane[]): Airplane[] {
    return [...planes].sort((a, b) => a.altitude - b.altitude);
  }

  getAltClass(altitude: number): string {
    const cat = getAltitudeCategory(altitude);
    return `alt-${cat}`;
  }

  getAltLabel(altitude: number): string {
    const cat = getAltitudeCategory(altitude);
    return cat === 'low' ? 'LOCAL' : cat === 'mid' ? 'DEPARTURE' : 'EN-ROUTE';
  }

  formatVelocity(v: number): string {
    return v != null ? `${Math.round(v)} kn` : '—';
  }

  formatAltitude(a: number): string {
    return a != null ? `${a.toLocaleString()} ft` : '—';
  }

  formatCoord(n: number): string {
    return n != null ? n.toFixed(4) : '—';
  }

  trackByCallsign(_: number, plane: Airplane): string {
    return plane.callsign;
  }

  ngOnDestroy(): void {
    this.monitorSub?.unsubscribe();
  }
}
