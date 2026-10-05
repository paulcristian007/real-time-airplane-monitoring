# Real-Time Airplane Monitoring App
A Python Django application that continuously ingests live aircraft data from the OpenSky Network API and provides fast geospatial queries through an optimized persistence layer.
The project focuses on scalability, efficient database updates, and concurrent read/write operations.
## Demo 

https://github.com/user-attachments/assets/5a079180-d41e-4f1b-b593-d2f0a35d23f0

## API 
- GET /fetch_airports
- GET /nearby_aircrafts?lat={latitude}&lng={longitude}
## Tech Stack
- Python
- Django
- Docker
- Redis
- Angular
- OpenSky API

# Architecture

The application continuously ingests aircraft data from the OpenSky Network API and exposes fast spatial queries through an optimized persistence layer.

## High-Level Workflow

1. A dedicated background worker runs continuously on a separate thread.
2. The worker fetches live aircraft data from the OpenSky API.
3. The received data is refined and transformed into the application's internal model.
4. The next application state is computed in memory.
5. A **single bulk database update** is performed, minimizing write overhead and reducing transaction costs.
6. Read requests are served from a backup read database, preventing race conditions while main database updates are in progress.
<p align="center">
<img width="533" height="444" alt="aircraft_architecture_final" src="https://github.com/user-attachments/assets/791bf588-09b1-462f-a5f1-a371ebbbc06e" /> 
</p>

---

# Design Decisions

## Persistence Layer

Although aircraft positions are refreshed every **5–10 seconds**, persistence plays an important role.

### Why persist the data?

* Provides a stable data source for read operations.
* Enables seamless failover if the primary backend becomes unavailable.
* Ensures uninterrupted query availability, which is critical in aviation-related systems.

The database consists of two tables:

| Table        | Purpose                                                                                                       |
| ------------ | ------------------------------------------------------------------------------------------------------------- |
| **Metadata** | Stores aircraft information such as coordinates, altitude, velocity, heading, callsign and ICAO24 identifier. |
| **Index**    | Stores the geohash associated with each aircraft for efficient spatial searches.                              |

Both tables are joined using the **ICAO24** identifier.

---

## In-Memory Cache

The application maintains the current aircraft state entirely in memory.

Instead of reading the previous state from the database, each update cycle computes the next state directly from the cached data.

This approach:

* Eliminates unnecessary database reads.
* Reduces latency.
* Minimizes database load during update cycles.

---
## Update Optimizations

### Metadata Optimization

During the cruise phase of a flight, several aircraft attributes remain almost constant.

Instead of updating these values every cycle, the application only persists them when the variation exceeds predefined thresholds.

Optimized fields include:

* Heading
* Velocity
* Altitude
* Callsign

<p align="center">
<img width="437" height="281" alt="update_visualisation" src="https://github.com/user-attachments/assets/2017b06d-6443-4b34-b942-155a4524e32b" />
</p>

---

### Geospatial Index Optimization

The aircraft geohash changes much less frequently than its coordinates.

Instead of recomputing and persisting the geohash every **5 seconds**, it is updated approximately every **5 minutes**, significantly reducing database writes while maintaining accurate spatial indexing.
<p align="center">
<img width="442" height="278" alt="index_visualisation" src="https://github.com/user-attachments/assets/b896e014-ffea-416e-835b-96220eb2796f" />
</p>




