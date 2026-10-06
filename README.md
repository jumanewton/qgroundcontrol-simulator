# QGroundControl Test Project

Project to test QGroundControl (QGC) and interact with vehicles on a map.

## Architecture

- **Vehicle Simulator**: Uses MAVSDK to simulate vehicles and expose a MAVLink microservice
- **Map Visualization**: Folium-based interactive map showing vehicle positions, waypoints, and flight paths
- **QGroundControl**: Connect QGC to the simulator via MAVLink to test the full ground control workflow

## Prerequisites

1. Python 3.9+
2. QGroundControl (install from https://qgroundcontrol.com/)
3. (Optional) MAVSDK backend if using SITL hardware-in-the-loop

## Setup

```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

## Usage

### Start the Vehicle Simulator

```bash
python src/simulator.py
```

### Start the Map Dashboard

```bash
python src/map_dashboard.py
```

Then open the generated HTML file in `maps/` or run the live server.

### Connect QGroundControl

1. Open QGroundControl
2. Go to Application Settings > Comm Links
3. Add a new UDP connection to `127.0.0.1:14540` (default MAVSDK server port)
4. Connect to the vehicle

## Project Structure

```
.
├── src/
│   ├── simulator.py      # MAVSDK-based vehicle simulation
│   ├── mission_planner.py # Waypoint and mission management
│   └── map_dashboard.py  # Folium map visualization
├── scripts/
│   ├── start_sim.bat     # Windows simulator launcher
│   ├── start_map.bat     # Windows map launcher
│   └── start_sim.sh      # Linux/Mac simulator launcher
├── maps/                 # Generated map HTML files
├── requirements.txt
└── README.md
```
