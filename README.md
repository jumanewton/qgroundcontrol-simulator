# QGroundControl Test Project

Project to test QGroundControl (QGC) and interact with vehicles on a map.

## Architecture

- **Vehicle Simulator**: Uses pymavlink to simulate a vehicle and expose a MAVLink endpoint
- **Map Visualization**: Folium-based interactive map showing vehicle positions, waypoints, and flight paths
- **QGroundControl**: Connect QGC to the simulator via MAVLink to test the full ground control workflow

## Prerequisites

1. Python 3.13+
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

1. Start the simulator with `python src\simulator.py`.
2. Open QGroundControl.
3. Go to **Application Settings > Comm Links**, add a **UDP** link, and set the port to `14550`.
4. Leave **Server Addresses** empty. Do not add `127.0.0.1:14550`; that is QGroundControl's own listening port.
5. Connect the link. The simulator sends a heartbeat from vehicle system ID `1`.
6. Use QGroundControl to arm/disarm, change modes, and upload a mission. The simulator writes the resulting state to `maps\telemetry.json`.

The simulator is a software test double, not a flight controller. Use it only on a local/test network and do not connect it to real vehicles.

To inspect telemetry once in PowerShell without locking the file, use:

```powershell
Get-Content .\maps\telemetry.json -Raw | ConvertFrom-Json | Format-List
```

Avoid `Get-Content ... -Wait` while the simulator is running on Windows because it can lock the file and prevent telemetry updates.

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
