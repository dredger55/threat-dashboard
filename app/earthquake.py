import httpx
from datetime import datetime, timedelta
import pytz
import math

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

# Home location (Monroe, WA)
HOME_LAT = 47.8554
HOME_LON = -121.971

# Distance calculation (Haversine formula)
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance_km = R * c
    return distance_km * 0.621371  # Convert to miles

async def get_earthquake_data():
    async with httpx.AsyncClient() as client:
        try:
            # USGS API for quakes in Puget Sound region (last 24 hours, min mag 1.0 for sensitivity)
            starttime = (datetime.utcnow() - timedelta(days=1)).isoformat() + "Z"
            usgs_url = (
                f"https://earthquake.usgs.gov/fdsnws/event/1/query?"
                f"format=geojson&starttime={starttime}&minmagnitude=1.0"
                f"&latitude={HOME_LAT}&longitude={HOME_LON}&maxradiuskm=400"  # ~250 miles for Puget Sound/Cascadia
            )
            usgs_resp = await client.get(usgs_url, timeout=10.0)
            usgs_resp.raise_for_status()
            usgs_data = usgs_resp.json()

            quakes = []
            major_quake = False
            for feature in usgs_data["features"][:10]:  # Last 10
                props = feature["properties"]
                geom = feature["geometry"]["coordinates"]  # lon, lat, depth
                mag = props["mag"] or 0
                place = props["place"]
                time = datetime.fromtimestamp(props["time"]/1000, tz=pytz.utc).astimezone(PACIFIC_TZ)
                depth_km = geom[2]
                distance = haversine(HOME_LAT, HOME_LON, geom[1], geom[0])
                felt = props.get("felt", 0) or 0
                detail_url = props["detail"]

                # Get aftershock info if available
                aftershock_info = ""
                detail_resp = await client.get(detail_url, timeout=5.0)
                if detail_resp.status_code == 200:
                    detail_json = detail_resp.json()
                    products = detail_json["properties"]["products"]
                    if "aftershock-forecast" in products:
                        aftershock_info = "Aftershock forecast available"

                style = "color:red; font-weight:bold;" if mag > 3.5 and distance <= 100 else ""
                quakes.append(f'<span style="{style}">'
                              f'{time.strftime("%H:%M")} | Mag {mag:.1f} | {place} | '
                              f'Depth {depth_km:.1f}km | {distance:.0f}mi away | '
                              f'Felt by {felt} people | {aftershock_info}'
                              f'</span>')

            # Tsunami warnings from NWS (already used in weather, but duplicate for reliability)
            alerts_resp = await client.get("https://api.weather.gov/alerts/active?area=WA", timeout=10.0)
            alerts_resp.raise_for_status()
            alerts = alerts_resp.json()["features"]
            tsunami_status = "No active tsunami alerts"
            for alert in alerts:
                if "tsunami" in alert["properties"]["event"].lower():
                    tsunami_status = f"TSUNAMI WARNING: {alert["properties"]["headline"]}"
                    major_quake = True  # Treat tsunami as severe

            return {
                "quakes": quakes,
                "major_quake": major_quake,
                "tsunami": tsunami_status,
                "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Earthquake API error: {e}")
            return {"error": str(e)}
