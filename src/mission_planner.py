import json
import math
import os
import requests

TELEMETRY_FILE = "D:/testCGQ/maps/telemetry.json"
MISSION_FILE = "D:/testCGQ/maps/mission.json"


def load_telemetry():
    with open(TELEMETRY_FILE, "r") as f:
        return json.load(f)


def save_telemetry(data):
    temp_file = f"{TELEMETRY_FILE}.{os.getpid()}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, TELEMETRY_FILE)


def load_mission():
    try:
        with open(MISSION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_mission(waypoints):
    temp_file = f"{MISSION_FILE}.{os.getpid()}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(waypoints, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, MISSION_FILE)


def add_waypoint(lat, lon, alt=50.0):
    waypoints = load_mission()
    waypoints.append({"lat": lat, "lon": lon, "alt": alt})
    save_mission(waypoints)
    print(f"Added waypoint: {lat}, {lon}, {alt}m")


def clear_waypoints():
    save_mission([])
    print("Cleared all waypoints")


def arm_vehicle(arm=True):
    data = load_telemetry()
    data["armed"] = arm
    save_telemetry(data)
    print(f"Vehicle {'armed' if arm else 'disarmed'}")


def set_mode(mode):
    data = load_telemetry()
    data["mode"] = mode
    save_telemetry(data)
    print(f"Mode set to: {mode}")


def get_telemetry():
    data = load_telemetry()
    print(json.dumps(data, indent=2))


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage:")
        print("  mission_planner.py arm")
        print("  mission_planner.py disarm")
        print("  mission_planner.py mode <GUIDED|LOITER|RTL>")
        print("  mission_planner.py waypoint <lat> <lon> [alt]")
        print("  mission_planner.py clear")
        print("  mission_planner.py status")
        return

    cmd = sys.argv[1]
    if cmd == "arm":
        arm_vehicle(True)
    elif cmd == "disarm":
        arm_vehicle(False)
    elif cmd == "mode":
        set_mode(sys.argv[2])
    elif cmd == "waypoint":
        lat = float(sys.argv[2])
        lon = float(sys.argv[3])
        alt = float(sys.argv[4]) if len(sys.argv) > 4 else 50.0
        add_waypoint(lat, lon, alt)
    elif cmd == "clear":
        clear_waypoints()
    elif cmd == "status":
        get_telemetry()
    else:
        print(f"Unknown command: {cmd}")


if __name__ == "__main__":
    main()
