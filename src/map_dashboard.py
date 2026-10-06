import json
import os
import time
from datetime import datetime
import folium
from folium import plugins

TELEMETRY_FILE = "D:/testCGQ/maps/telemetry.json"
OUTPUT_HTML = "D:/testCGQ/maps/dashboard.html"


def load_telemetry():
    try:
        with open(TELEMETRY_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


def create_map():
    data = load_telemetry()
    if not data:
        print("No telemetry data available yet. Start the simulator first.")
        return

    lat = data.get("lat", 47.397742)
    lon = data.get("lon", 8.545594)
    alt = data.get("alt", 500.0)
    heading = data.get("heading", 0.0)
    mode = data.get("mode", "UNKNOWN")
    armed = data.get("armed", False)
    battery = data.get("battery", 0.0)
    waypoints = data.get("waypoints", [])
    current_wp = data.get("current_waypoint", -1)
    timestamp = data.get("timestamp", "")

    m = folium.Map(location=[lat, lon], zoom_start=16, tiles="OpenStreetMap")
    folium.TileLayer("CartoDB positron", name="Light Map").add_to(m)

    if waypoints:
        wp_coords = []
        for i, wp in enumerate(waypoints):
            color = "green" if i == current_wp else "blue"
            folium.Marker(
                [wp["lat"], wp["lon"]],
                popup=f"WP {i+1}<br>Alt: {wp['alt']:.1f}m",
                icon=folium.Icon(color=color, icon="flag" if i == current_wp else "info-sign")
            ).add_to(m)
            wp_coords.append([wp["lat"], wp["lon"]])

        if len(wp_coords) > 1:
            folium.PolyLine(wp_coords, color="blue", weight=2, opacity=0.7).add_to(m)

    vehicle_icon = folium.DivIcon(
        html=f'<div style="font-size:24px; transform: rotate({heading}deg);">✈️</div>',
        icon_size=(30, 30),
        icon_anchor=(15, 15)
    )
    folium.Marker(
        [lat, lon],
        popup=f"Vehicle<br>Alt: {alt:.1f}m<br>Mode: {mode}<br>Armed: {armed}<br>Battery: {battery:.1f}%<br>Heading: {heading:.1f}°<br>Updated: {timestamp}",
        icon=vehicle_icon
    ).add_to(m)

    plugins.Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>QGC Test Dashboard</title>
    <meta http-equiv="refresh" content="2">
    <style>
        body {{ margin: 0; padding: 0; font-family: Arial, sans-serif; }}
        #info {{ position: absolute; top: 10px; right: 10px; background: white; padding: 10px; z-index: 1000; border-radius: 5px; box-shadow: 0 0 5px rgba(0,0,0,0.3); }}
        #info h3 {{ margin: 0 0 10px 0; font-size: 16px; }}
        #info p {{ margin: 3px 0; font-size: 12px; }}
    </style>
</head>
<body>
    <div id="info">
        <h3>Vehicle Telemetry</h3>
        <p><strong>Lat:</strong> {lat:.6f}</p>
        <p><strong>Lon:</strong> {lon:.6f}</p>
        <p><strong>Alt:</strong> {alt:.1f} m</p>
        <p><strong>Mode:</strong> {mode}</p>
        <p><strong>Armed:</strong> {"Yes" if armed else "No"}</p>
        <p><strong>Battery:</strong> {battery:.1f}%</p>
        <p><strong>Heading:</strong> {heading:.1f}°</p>
        <p><strong>Updated:</strong> {timestamp}</p>
    </div>
    {m._repr_html_()}
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Dashboard updated: {OUTPUT_HTML}")


def main():
    print("Starting map dashboard...")
    print(f"Open {OUTPUT_HTML} in your browser")
    try:
        while True:
            create_map()
            time.sleep(2)
    except KeyboardInterrupt:
        print("Shutting down dashboard...")


if __name__ == "__main__":
    main()
