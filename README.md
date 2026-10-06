# QGroundControl Simulator

A local MAVLink vehicle simulator for testing QGroundControl (QGC), vehicle
commands, waypoint missions, takeoff and landing behavior, and live telemetry
on a map. This project is a software test double, not a real flight controller.

## Architecture

- **Vehicle simulator**: Uses `pymavlink` and exposes a MAVLink UDP endpoint.
- **Map dashboard**: Uses Folium and Leaflet to display live vehicle telemetry.
- **Mission planner**: Provides a small command-line interface for adding,
  clearing, and inspecting test waypoints.
- **QGroundControl**: Connects over UDP for testing the end-to-end workflow.

## Features

- MAVLink heartbeat, GPS, position, system-status, parameter, and mission
  protocol support.
- Arm/disarm and flight-mode commands.
- Simulated takeoff and landing at 5 m/s.
- Waypoint navigation while armed.
- Mission start support through QGroundControl.
- Mission completion at the final waypoint; missions do not loop.
- Live dashboard updates without reloading the map.
- OpenStreetMap tiles with no map API key required.

## Prerequisites

- Python 3.13 or newer
- QGroundControl: https://qgroundcontrol.com/
- Internet access for map tiles and browser JavaScript dependencies

## Setup

On Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

On Linux or macOS:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Start the Vehicle Simulator

```powershell
python src/simulator.py
```

### Start the Map Dashboard

In a second terminal:

```powershell
python src/map_dashboard.py
```

In a third terminal, serve the generated dashboard:

```powershell
cd maps
python -m http.server 8000
```

Open http://localhost:8000/dashboard.html.

### Connect QGroundControl

1. Open QGroundControl.
2. Go to **Application Settings > Comm Links**.
3. Add a UDP link using port `14550`.
4. Leave **Server Addresses** empty. Do not add
   `127.0.0.1:14550`; that is QGroundControl's listening port.
5. Connect the link. The simulator sends a heartbeat from vehicle system ID 1.

The simulator models takeoff and landing movement. After arming, a takeoff command
climbs at 5 m/s toward the requested relative altitude. A land command descends
to the simulated home altitude and disarms when it reaches the ground.

### Test a waypoint mission

To see the vehicle move across the map:

1. Start the simulator and connect QGroundControl.
2. In QGroundControl, open **Plan**, add a takeoff command and two or more
   waypoints near the vehicle position (`47.397742, 8.545594`), then upload the
   mission.
3. Arm the vehicle and start the mission, or send takeoff first and then start
   the mission.
4. Run `python src\map_dashboard.py` in a second terminal and open
   `maps\dashboard.html`. The vehicle marker moves toward the current waypoint.

For a quick file-based test, add nearby waypoints:

```powershell
python src\mission_planner.py waypoint 47.398500 8.545594 10
python src\mission_planner.py waypoint 47.398500 8.547000 10
```

The simulator follows waypoints while armed. It advances to the next waypoint
when it is within approximately 11 meters and stops at the final waypoint.
Use QGroundControl's **Start Mission** command or the mission planner commands
above to test the route.

Mission-planner waypoints are stored separately in `maps\mission.json` so the
simulator's high-frequency telemetry updates cannot overwrite them.

The simulator is a software test double, not a flight controller. Use it only on a local/test network and do not connect it to real vehicles.

The map dashboard uses OpenStreetMap tiles and does not require a map API key.

To inspect telemetry once in PowerShell without locking the file, use:

```powershell
Get-Content .\maps\telemetry.json -Raw | ConvertFrom-Json | Format-List
```

Avoid `Get-Content ... -Wait` while the simulator is running on Windows because it can lock the file and prevent telemetry updates.

## Project Structure

```
.
├── src/
│   ├── simulator.py       # MAVLink vehicle simulation
│   ├── mission_planner.py # Waypoint and mission management
│   └── map_dashboard.py   # Folium live dashboard
├── scripts/               # Windows and Unix launch scripts
├── maps/                  # Generated dashboard and runtime state
├── requirements.txt
└── README.md
```

## Runtime files

The simulator generates these files under `maps/`:

- `telemetry.json` — current vehicle state.
- `mission.json` — file-based test mission.
- `dashboard.html` — generated map dashboard.

They are ignored by Git and should not be committed.

## Safety

Use this project only on a local or test network. It is not a certified flight
controller and must not be connected to real vehicles or used for real flight.

## License

No license has been selected yet. Add a license before redistributing the
project or accepting external contributions.
