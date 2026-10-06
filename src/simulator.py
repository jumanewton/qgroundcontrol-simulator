import socket
import time
import json
import math
import threading
from datetime import datetime

from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

UDP_IP = "127.0.0.1"
UDP_PORT = 14550
TELEMETRY_FILE = "D:/testCGQ/maps/telemetry.json"

HEARTBEAT_INTERVAL = 1.0
GPS_INTERVAL = 0.5
POSITION_INTERVAL = 0.2

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

vehicle_state = {
    "lat": 47.397742,
    "lon": 8.545594,
    "alt": 500.0,
    "heading": 0.0,
    "speed": 5.0,
    "armed": False,
    "mode": "GUIDED",
    "battery": 100.0,
    "waypoints": [],
    "current_waypoint": -1,
    "timestamp": datetime.now().isoformat()
}

telemetry_lock = threading.Lock()


def save_telemetry():
    with telemetry_lock:
        with open(TELEMETRY_FILE, "w") as f:
            json.dump(vehicle_state, f, indent=2)


def create_mavlink():
    m = mavlink2.MAVLink(None)
    m.robust_parsing = True
    return m


def send_heartbeat(mav):
    while True:
        msg = mav.heartbeat_encode(
            type=mavlink2.MAV_TYPE_QUADROTOR,
            autopilot=mavlink2.MAV_AUTOPILOT_GENERIC,
            base_mode=0,
            custom_mode=0,
            system_status=mavlink2.MAV_STATE_STANDBY
        )
        data = msg.pack(mav)
        sock.sendto(data, (UDP_IP, UDP_PORT))
        time.sleep(HEARTBEAT_INTERVAL)


def send_gps_raw(mav):
    while True:
        lat = int(vehicle_state["lat"] * 1e7)
        lon = int(vehicle_state["lon"] * 1e7)
        alt = int(vehicle_state["alt"] * 1000.0)
        msg = mav.gps_raw_int_encode(
            time_usec=int(time.time() * 1e6),
            fix_type=3,
            lat=lat,
            lon=lon,
            alt=alt,
            eph=65535,
            epv=65535,
            vel=200,
            cog=int(vehicle_state["heading"] * 100),
            satellites_visible=10
        )
        data = msg.pack(mav)
        sock.sendto(data, (UDP_IP, UDP_PORT))
        time.sleep(GPS_INTERVAL)


def send_global_position(mav):
    while True:
        lat = int(vehicle_state["lat"] * 1e7)
        lon = int(vehicle_state["lon"] * 1e7)
        alt = int(vehicle_state["alt"] * 1000.0)
        rel_alt = int(vehicle_state["alt"] * 1000.0)
        hdg = int((vehicle_state["heading"] * 100) % 36000)
        msg = mav.global_position_int_encode(
            time_boot_ms=int((time.time() * 1000) % 4294967295),
            lat=lat,
            lon=lon,
            alt=alt,
            relative_alt=rel_alt,
            vx=0,
            vy=0,
            vz=0,
            hdg=hdg
        )
        data = msg.pack(mav)
        sock.sendto(data, (UDP_IP, UDP_PORT))
        time.sleep(POSITION_INTERVAL)


def send_sys_status(mav):
    while True:
        msg = mav.sys_status_encode(
            onboard_control_sensors_present=0,
            onboard_control_sensors_enabled=0,
            onboard_control_sensors_health=0,
            load=0,
            voltage_battery=12500,
            current_battery=500,
            battery_remaining=int(vehicle_state["battery"]),
            drop_rate_comm=0,
            errors_comm=0,
            errors_count1=0,
            errors_count2=0,
            errors_count3=0,
            errors_count4=0
        )
        data = msg.pack(mav)
        sock.sendto(data, (UDP_IP, UDP_PORT))
        time.sleep(2.0)


def update_telemetry():
    while True:
        with telemetry_lock:
            if vehicle_state["armed"] and vehicle_state["waypoints"]:
                wp = vehicle_state["waypoints"][vehicle_state["current_waypoint"]]
                target_lat = wp["lat"]
                target_lon = wp["lon"]
                dist = math.sqrt((target_lat - vehicle_state["lat"])**2 + (target_lon - vehicle_state["lon"])**2)
                if dist < 0.0001:
                    vehicle_state["current_waypoint"] = (vehicle_state["current_waypoint"] + 1) % len(vehicle_state["waypoints"])
                else:
                    vehicle_state["lat"] += (target_lat - vehicle_state["lat"]) * 0.05
                    vehicle_state["lon"] += (target_lon - vehicle_state["lon"]) * 0.05
                    bearing = math.degrees(math.atan2(target_lon - vehicle_state["lon"], target_lat - vehicle_state["lat"]))
                    vehicle_state["heading"] = bearing % 360
            vehicle_state["timestamp"] = datetime.now().isoformat()
            vehicle_state["battery"] = max(0, vehicle_state["battery"] - 0.001)
        save_telemetry()
        time.sleep(0.1)


def listen_for_commands(mav):
    while True:
        try:
            data, _ = sock.recvfrom(4096)
            for msg in mav.parse_buffer(data):
                if msg.get_type() == 'COMMAND_LONG':
                    cmd = msg.command
                    if cmd == mavlink2.MAV_CMD_COMPONENT_ARM_DISARM:
                        arm = msg.param1
                        with telemetry_lock:
                            vehicle_state["armed"] = bool(round(arm))
                            print(f"Vehicle {'armed' if vehicle_state['armed'] else 'disarmed'}")
                    elif cmd == mavlink2.MAV_CMD_DO_SET_MODE:
                        mode = int(msg.param1)
                        modes = {0: "MANUAL", 1: "GUIDED", 4: "AUTO", 6: "RTL", 9: "LOITER"}
                        with telemetry_lock:
                            vehicle_state["mode"] = modes.get(mode, f"MODE_{mode}")
                            print(f"Mode set to: {vehicle_state['mode']}")
                elif msg.get_type() == 'MISSION_ITEM':
                    with telemetry_lock:
                        lat = msg.x / 1e7
                        lon = msg.y / 1e7
                        alt = msg.z
                        vehicle_state["waypoints"].append({"lat": lat, "lon": lon, "alt": alt})
                        vehicle_state["current_waypoint"] = 0
                        print(f"Waypoint received: {lat}, {lon}, {alt}")
                elif msg.get_type() == 'MISSION_CLEAR_ALL':
                    with telemetry_lock:
                        vehicle_state["waypoints"] = []
                        vehicle_state["current_waypoint"] = -1
                        print("Mission cleared")
        except Exception:
            pass


def main():
    print(f"Starting vehicle simulator on UDP {UDP_IP}:{UDP_PORT}")
    print(f"Telemetry written to: {TELEMETRY_FILE}")
    print("Waiting for QGroundControl connection...")

    mav = create_mavlink()

    threads = [
        threading.Thread(target=send_heartbeat, args=(mav,), daemon=True),
        threading.Thread(target=send_gps_raw, args=(mav,), daemon=True),
        threading.Thread(target=send_global_position, args=(mav,), daemon=True),
        threading.Thread(target=send_sys_status, args=(mav,), daemon=True),
        threading.Thread(target=update_telemetry, daemon=True),
        threading.Thread(target=listen_for_commands, args=(mav,), daemon=True),
    ]

    for t in threads:
        t.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down simulator...")


if __name__ == "__main__":
    main()