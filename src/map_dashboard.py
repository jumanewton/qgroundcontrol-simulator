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
    vehicle_marker = folium.Marker(
        [lat, lon],
        popup=f"Vehicle<br>Alt: {alt:.1f}m<br>Mode: {mode}<br>Armed: {armed}<br>Battery: {battery:.1f}%<br>Heading: {heading:.1f}°<br>Updated: {timestamp}",
        icon=vehicle_icon
    ).add_to(m)

    plugins.Fullscreen().add_to(m)
    folium.LayerControl().add_to(m)

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>QGC Test Dashboard</title>
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
        <p><strong>Lat:</strong> <span id="lat">{lat:.6f}</span></p>
        <p><strong>Lon:</strong> <span id="lon">{lon:.6f}</span></p>
        <p><strong>Alt:</strong> <span id="alt">{alt:.1f} m</span></p>
        <p><strong>Mode:</strong> <span id="mode">{mode}</span></p>
        <p><strong>Armed:</strong> <span id="armed">{"Yes" if armed else "No"}</span></p>
        <p><strong>Battery:</strong> <span id="battery">{battery:.1f}%</span></p>
        <p><strong>Heading:</strong> <span id="heading">{heading:.1f}°</span></p>
        <p><strong>Updated:</strong> <span id="timestamp">{timestamp}</span></p>
    </div>
    {m.get_root().render()}
    <script>
        const map = {m.get_name()};
        const vehicleMarker = {vehicle_marker.get_name()};

        function updateTelemetry() {{
            fetch("telemetry.json?timestamp=" + Date.now())
                .then(response => response.json())
                .then(data => {{
                    const position = [data.lat, data.lon];
                    vehicleMarker.setLatLng(position);
                    vehicleMarker.setIcon(L.divIcon({{
                        html: '<div style="font-size:24px; transform: rotate(' + data.heading + 'deg);">✈️</div>',
                        iconSize: [30, 30],
                        iconAnchor: [15, 15]
                    }}));
                    vehicleMarker.setPopupContent(
                        'Vehicle<br>Alt: ' + data.alt.toFixed(1) +
                        'm<br>Mode: ' + data.mode +
                        '<br>Armed: ' + data.armed +
                        '<br>Battery: ' + data.battery.toFixed(1) +
                        '%<br>Heading: ' + data.heading.toFixed(1) +
                        '°<br>Updated: ' + data.timestamp
                    );
                    document.getElementById("lat").textContent = data.lat.toFixed(6);
                    document.getElementById("lon").textContent = data.lon.toFixed(6);
                    document.getElementById("alt").textContent = data.alt.toFixed(1) + " m";
                    document.getElementById("mode").textContent = data.mode;
                    document.getElementById("armed").textContent = data.armed ? "Yes" : "No";
                    document.getElementById("battery").textContent = data.battery.toFixed(1) + "%";
                    document.getElementById("heading").textContent = data.heading.toFixed(1) + "°";
                    document.getElementById("timestamp").textContent = data.timestamp;
                }})
                .catch(() => {{}});
        }}

        setInterval(updateTelemetry, 500);
    </script>
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
