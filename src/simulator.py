import socket
import time
import json
import math
import os
import threading
from datetime import datetime

from pymavlink import mavutil
from pymavlink.dialects.v20 import common as mavlink2

UDP_IP = "127.0.0.1"
UDP_PORT = 14550
TELEMETRY_FILE = "D:/testCGQ/maps/telemetry.json"
MISSION_FILE = "D:/testCGQ/maps/mission.json"
SYSTEM_ID = 1
COMPONENT_ID = mavlink2.MAV_COMP_ID_AUTOPILOT1

HEARTBEAT_INTERVAL = 1.0
GPS_INTERVAL = 0.5
POSITION_INTERVAL = 0.2
HOME_ALTITUDE = 500.0
VERTICAL_SPEED = 5.0
TELEMETRY_WRITE_RETRIES = 5
TELEMETRY_WRITE_RETRY_DELAY = 0.1
last_telemetry_write_ns = 0

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, 0))

vehicle_state = {
    "lat": 47.397742,
    "lon": 8.545594,
    "alt": HOME_ALTITUDE,
    "flight_target_alt": None,
    "heading": 0.0,
    "speed": 5.0,
    "armed": False,
    "mode": "GUIDED",
    "battery": 100.0,
    "waypoints": [],
    "current_waypoint": -1,
    "mission_complete": False,
    "timestamp": datetime.now().isoformat()
}

telemetry_lock = threading.Lock()

# A small parameter set is enough for QGroundControl to complete vehicle
# initialization. Parameters are also writable through PARAM_SET.
parameters = {
    "SYSID_THISMAV": 1.0,
    "SYSID_COMPID": float(COMPONENT_ID),
    "FRAME_CLASS": 1.0,
    "FRAME_TYPE": 1.0,
    "RTL_ALT": 150.0,
    "WPNAV_SPEED": 500.0,
    "RCMAP_ROLL": 1.0,
    "RCMAP_PITCH": 2.0,
    "RCMAP_YAW": 4.0,
    "RCMAP_THROTTLE": 3.0,
    "RCO_MIN": 1100.0,
    "RCO_MAX": 1900.0,
    "RCO_TRIM": 1500.0,
    "RC1_MIN": 1100.0,
    "RC1_MAX": 1900.0,
    "RC1_TRIM": 1500.0,
    "RC2_MIN": 1100.0,
    "RC2_MAX": 1900.0,
    "RC2_TRIM": 1500.0,
    "RC3_MIN": 1100.0,
    "RC3_MAX": 1900.0,
    "RC3_TRIM": 1500.0,
    "RC4_MIN": 1100.0,
    "RC4_MAX": 1900.0,
    "RC4_TRIM": 1500.0,
    "COMPASS_DEV_ID": 0.0,
    "COMPASS_DEV_ID2": 0.0,
    "COMPASS_DEV_ID3": 0.0,
    "INS_ACCOFFS_X": 0.0,
    "INS_ACCOFFS_Y": 0.0,
    "INS_ACCOFFS_Z": 0.0,
    "FS_OPTIONS": 0.0,
    "FS_GCS_TIMEOUT": 5.0,
    "FS_GCS_ENABLE": 0.0,
}


def save_telemetry(state):
    global last_telemetry_write_ns
    temp_file = f"{TELEMETRY_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    for attempt in range(TELEMETRY_WRITE_RETRIES):
        try:
            os.replace(temp_file, TELEMETRY_FILE)
            last_telemetry_write_ns = os.stat(TELEMETRY_FILE).st_mtime_ns
            return
        except PermissionError:
            if attempt + 1 < TELEMETRY_WRITE_RETRIES:
                time.sleep(TELEMETRY_WRITE_RETRY_DELAY)
    print(
        f"Telemetry file is locked: {TELEMETRY_FILE}. "
        "Close any Get-Content -Wait window and retry."
    )
    try:
        os.remove(temp_file)
    except FileNotFoundError:
        pass


def load_telemetry():
    try:
        with open(TELEMETRY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def sync_from_file():
    while True:
        try:
            time.sleep(1.0)
            data = load_telemetry()
            mission = load_json_file(MISSION_FILE)
            if data:
                with telemetry_lock:
                    if "armed" in data:
                        vehicle_state["armed"] = data["armed"]
                    if "mode" in data:
                        vehicle_state["mode"] = data["mode"]
                    if mission is not None:
                        mission_changed = mission != vehicle_state["waypoints"]
                        vehicle_state["waypoints"] = mission
                        if mission_changed:
                            vehicle_state["mission_complete"] = False
                        if vehicle_state["current_waypoint"] >= len(mission):
                            vehicle_state["current_waypoint"] = 0 if mission else -1
        except Exception as e:
            print(f"Sync error: {e}")


def load_json_file(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_mission(waypoints):
    temp_file = f"{MISSION_FILE}.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(waypoints, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_file, MISSION_FILE)


def create_mavlink():
    m = mavlink2.MAVLink(
        None,
        srcSystem=SYSTEM_ID,
        srcComponent=COMPONENT_ID,
    )
    m.robust_parsing = True
    return m


def send_heartbeat(mav):
    while True:
        with telemetry_lock:
            armed = vehicle_state["armed"]
            mode = vehicle_state["mode"]
        mode_ids = {"STABILIZE": 0, "AUTO": 3, "GUIDED": 4, "LOITER": 5, "RTL": 6, "LAND": 9}
        base_mode = mavlink2.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        if armed:
            base_mode |= mavlink2.MAV_MODE_FLAG_SAFETY_ARMED
        msg = mav.heartbeat_encode(
            type=mavlink2.MAV_TYPE_QUADROTOR,
            autopilot=mavlink2.MAV_AUTOPILOT_ARDUPILOTMEGA,
            base_mode=base_mode,
            custom_mode=mode_ids.get(mode, 4),
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
        rel_alt = int((vehicle_state["alt"] - HOME_ALTITUDE) * 1000.0)
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
        try:
            with telemetry_lock:
                target_alt = vehicle_state["flight_target_alt"]
                if target_alt is not None:
                    altitude_delta = target_alt - vehicle_state["alt"]
                    altitude_step = VERTICAL_SPEED * 0.1
                    if abs(altitude_delta) <= altitude_step:
                        vehicle_state["alt"] = target_alt
                        vehicle_state["flight_target_alt"] = None
                        if target_alt <= HOME_ALTITUDE:
                            vehicle_state["armed"] = False
                    else:
                        vehicle_state["alt"] += math.copysign(altitude_step, altitude_delta)

                if vehicle_state["armed"] and vehicle_state["waypoints"]:
                    if vehicle_state["current_waypoint"] < 0:
                        vehicle_state["current_waypoint"] = 0
                    wp = vehicle_state["waypoints"][vehicle_state["current_waypoint"]]
                    target_lat = wp["lat"]
                    target_lon = wp["lon"]
                    dist = math.sqrt((target_lat - vehicle_state["lat"])**2 + (target_lon - vehicle_state["lon"])**2)
                    if dist < 0.0001:
                        if vehicle_state["current_waypoint"] == len(vehicle_state["waypoints"]) - 1:
                            if not vehicle_state["mission_complete"]:
                                print("Mission complete")
                            vehicle_state["mission_complete"] = True
                        else:
                            vehicle_state["current_waypoint"] += 1
                    else:
                        vehicle_state["lat"] += (target_lat - vehicle_state["lat"]) * 0.05
                        vehicle_state["lon"] += (target_lon - vehicle_state["lon"]) * 0.05
                        bearing = math.degrees(math.atan2(target_lon - vehicle_state["lon"], target_lat - vehicle_state["lat"]))
                        vehicle_state["heading"] = bearing % 360
                vehicle_state["timestamp"] = datetime.now().isoformat()
                vehicle_state["battery"] = max(0, vehicle_state["battery"] - 0.001)
                state_copy = vehicle_state.copy()
            save_telemetry(state_copy)
        except Exception as e:
            print(f"Update telemetry error: {e}")
        time.sleep(0.1)


def send_command_ack(mav, msg, result, addr):
    ack = mav.command_ack_encode(
        command=msg.command,
        result=result,
        progress=0,
        result_param2=0,
        target_system=msg.get_srcSystem(),
        target_component=msg.get_srcComponent(),
    )
    sock.sendto(ack.pack(mav), addr)


def send_mission_ack(mav, msg, result, addr):
    ack = mav.mission_ack_encode(
        target_system=msg.get_srcSystem(),
        target_component=msg.get_srcComponent(),
        type=result,
        mission_type=getattr(msg, "mission_type", mavlink2.MAV_MISSION_TYPE_MISSION),
    )
    sock.sendto(ack.pack(mav), addr)


def send_parameters(mav, addr):
    parameter_items = list(parameters.items())
    for index, (param_id, value) in enumerate(parameter_items):
        message = mav.param_value_encode(
            param_id=param_id.encode("ascii"),
            param_value=value,
            param_type=mavlink2.MAV_PARAM_TYPE_REAL32,
            param_count=len(parameter_items),
            param_index=index,
        )
        sock.sendto(message.pack(mav), addr)


def send_mission_count(mav, msg, addr):
    mission_type = getattr(msg, "mission_type", mavlink2.MAV_MISSION_TYPE_MISSION)
    with telemetry_lock:
        count = len(vehicle_state["waypoints"]) if mission_type == mavlink2.MAV_MISSION_TYPE_MISSION else 0
    message = mav.mission_count_encode(
        target_system=msg.get_srcSystem(),
        target_component=msg.get_srcComponent(),
        count=count,
        mission_type=mission_type,
    )
    sock.sendto(message.pack(mav), addr)


def send_mission_item(mav, msg, addr):
    mission_type = getattr(msg, "mission_type", mavlink2.MAV_MISSION_TYPE_MISSION)
    sequence = msg.seq
    with telemetry_lock:
        waypoints = list(vehicle_state["waypoints"])
    if mission_type != mavlink2.MAV_MISSION_TYPE_MISSION or sequence >= len(waypoints):
        send_mission_ack(mav, msg, mavlink2.MAV_MISSION_INVALID_SEQUENCE, addr)
        return

    waypoint = waypoints[sequence]
    item = mav.mission_item_int_encode(
        target_system=msg.get_srcSystem(),
        target_component=msg.get_srcComponent(),
        seq=sequence,
        frame=mavlink2.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
        command=mavlink2.MAV_CMD_NAV_WAYPOINT,
        current=1 if sequence == 0 else 0,
        autocontinue=1,
        param1=0,
        param2=0,
        param3=0,
        param4=0,
        x=int(waypoint["lat"] * 1e7),
        y=int(waypoint["lon"] * 1e7),
        z=float(waypoint.get("alt", 0)),
        mission_type=mission_type,
    )
    sock.sendto(item.pack(mav), addr)


def listen_for_commands(mav):
    mission_upload = []
    expected_mission_count = None
    while True:
        try:
            data, addr = sock.recvfrom(4096)
            for msg in mav.parse_buffer(data):
                if msg.get_type() in ('COMMAND_LONG', 'COMMAND_INT'):
                    cmd = msg.command
                    if cmd == mavlink2.MAV_CMD_COMPONENT_ARM_DISARM:
                        arm = msg.param1
                        with telemetry_lock:
                            vehicle_state["armed"] = bool(round(arm))
                            print(f"Vehicle {'armed' if vehicle_state['armed'] else 'disarmed'}")
                        send_command_ack(mav, msg, mavlink2.MAV_RESULT_ACCEPTED, addr)
                    elif cmd == mavlink2.MAV_CMD_DO_SET_MODE:
                        mode = int(msg.param2)
                        modes = {0: "STABILIZE", 3: "AUTO", 4: "GUIDED", 5: "LOITER", 6: "RTL", 9: "LAND"}
                        with telemetry_lock:
                            vehicle_state["mode"] = modes.get(mode, f"MODE_{mode}")
                            print(f"Mode set to: {vehicle_state['mode']}")
                        send_command_ack(mav, msg, mavlink2.MAV_RESULT_ACCEPTED, addr)
                    elif cmd == mavlink2.MAV_CMD_MISSION_START:
                        with telemetry_lock:
                            has_mission = bool(vehicle_state["waypoints"])
                            if has_mission:
                                vehicle_state["current_waypoint"] = 0
                                vehicle_state["mission_complete"] = False
                                vehicle_state["mode"] = "AUTO"
                        if has_mission:
                            print("Mission started")
                            result = mavlink2.MAV_RESULT_ACCEPTED
                        else:
                            print("Mission start rejected: no waypoints loaded")
                            result = mavlink2.MAV_RESULT_DENIED
                        send_command_ack(mav, msg, result, addr)
                    elif cmd in (mavlink2.MAV_CMD_NAV_TAKEOFF, mavlink2.MAV_CMD_NAV_LAND):
                        if cmd == mavlink2.MAV_CMD_NAV_TAKEOFF:
                            requested_altitude = msg.param7 if msg.get_type() == "COMMAND_LONG" else msg.z
                            with telemetry_lock:
                                takeoff_altitude = max(
                                    HOME_ALTITUDE + max(float(requested_altitude), 10.0),
                                    vehicle_state["alt"],
                                )
                                vehicle_state["flight_target_alt"] = takeoff_altitude
                            action = f"takeoff to {takeoff_altitude:.1f}m AMSL"
                        else:
                            with telemetry_lock:
                                vehicle_state["flight_target_alt"] = HOME_ALTITUDE
                            action = "land"
                        print(f"{action.capitalize()} command accepted")
                        send_command_ack(mav, msg, mavlink2.MAV_RESULT_ACCEPTED, addr)
                    else:
                        send_command_ack(mav, msg, mavlink2.MAV_RESULT_UNSUPPORTED, addr)
                elif msg.get_type() == 'SET_MODE':
                    mode_ids = {0: "STABILIZE", 3: "AUTO", 4: "GUIDED", 5: "LOITER", 6: "RTL", 9: "LAND"}
                    with telemetry_lock:
                        vehicle_state["mode"] = mode_ids.get(msg.custom_mode, f"MODE_{msg.custom_mode}")
                    print(f"Mode set to: {vehicle_state['mode']}")
                elif msg.get_type() == 'PARAM_REQUEST_LIST':
                    send_parameters(mav, addr)
                elif msg.get_type() == 'PARAM_REQUEST_READ':
                    requested_id = msg.param_id.rstrip(b"\x00").decode("ascii", errors="ignore")
                    if requested_id in parameters:
                        parameter_items = list(parameters.items())
                        index = [name for name, _ in parameter_items].index(requested_id)
                        response = mav.param_value_encode(
                            param_id=msg.param_id,
                            param_value=parameters[requested_id],
                            param_type=mavlink2.MAV_PARAM_TYPE_REAL32,
                            param_count=len(parameter_items),
                            param_index=index,
                        )
                        sock.sendto(response.pack(mav), addr)
                elif msg.get_type() == 'PARAM_SET':
                    parameter_id = msg.param_id.rstrip(b"\x00").decode("ascii", errors="ignore")
                    if parameter_id in parameters:
                        parameters[parameter_id] = msg.param_value
                        parameter_items = list(parameters.items())
                        index = [name for name, _ in parameter_items].index(parameter_id)
                        response = mav.param_value_encode(
                            param_id=msg.param_id,
                            param_value=parameters[parameter_id],
                            param_type=mavlink2.MAV_PARAM_TYPE_REAL32,
                            param_count=len(parameter_items),
                            param_index=index,
                        )
                        sock.sendto(response.pack(mav), addr)
                elif msg.get_type() == 'MISSION_REQUEST_LIST':
                    send_mission_count(mav, msg, addr)
                elif msg.get_type() in ('MISSION_REQUEST_INT', 'MISSION_REQUEST'):
                    send_mission_item(mav, msg, addr)
                elif msg.get_type() == 'MISSION_COUNT':
                    expected_mission_count = msg.count
                    mission_upload = []
                    request = mav.mission_request_int_encode(
                        target_system=msg.get_srcSystem(),
                        target_component=msg.get_srcComponent(),
                        seq=0,
                        mission_type=getattr(msg, "mission_type", mavlink2.MAV_MISSION_TYPE_MISSION),
                    )
                    sock.sendto(request.pack(mav), addr)
                elif msg.get_type() in ('MISSION_ITEM_INT', 'MISSION_ITEM'):
                    if msg.get_type() == 'MISSION_ITEM_INT':
                        lat = msg.x / 1e7
                        lon = msg.y / 1e7
                    else:
                        lat = msg.x
                        lon = msg.y
                    mission_upload.append({"lat": lat, "lon": lon, "alt": msg.z})
                    if expected_mission_count is not None and len(mission_upload) < expected_mission_count:
                        request = mav.mission_request_int_encode(
                            target_system=msg.get_srcSystem(),
                            target_component=msg.get_srcComponent(),
                            seq=len(mission_upload),
                            mission_type=getattr(msg, "mission_type", mavlink2.MAV_MISSION_TYPE_MISSION),
                        )
                        sock.sendto(request.pack(mav), addr)
                    else:
                        with telemetry_lock:
                            vehicle_state["waypoints"] = mission_upload
                            vehicle_state["current_waypoint"] = 0 if mission_upload else -1
                            vehicle_state["mission_complete"] = False
                        save_mission(mission_upload)
                        send_mission_ack(mav, msg, mavlink2.MAV_MISSION_ACCEPTED, addr)
                        expected_mission_count = None
                        print(f"Mission received: {len(mission_upload)} waypoint(s)")
                elif msg.get_type() == 'MISSION_CLEAR_ALL':
                    with telemetry_lock:
                        vehicle_state["waypoints"] = []
                        vehicle_state["current_waypoint"] = -1
                        vehicle_state["mission_complete"] = False
                    save_mission([])
                    send_mission_ack(mav, msg, mavlink2.MAV_MISSION_ACCEPTED, addr)
                    print("Mission cleared")
        except (OSError, ValueError) as e:
            print(f"Command receive error: {e}")


def main():
    print(f"Starting vehicle simulator on UDP {UDP_IP}:{UDP_PORT}")
    print(f"Simulator command socket bound to {sock.getsockname()[0]}:{sock.getsockname()[1]}")
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
        threading.Thread(target=sync_from_file, daemon=True),
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