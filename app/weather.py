import httpx
from datetime import datetime
import pytz
import re

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

# Monroe, WA coordinates for NWS point
MONROE_LAT = 47.8554
MONROE_LON = -121.971

# NWS API endpoints
POINTS_URL = f"https://api.weather.gov/points/{MONROE_LAT},{MONROE_LON}"
OBSERVATION_URL = "https://api.weather.gov/stations/KPAE/observations/latest"  # Closest station Paine Field
ALERTS_URL = "https://api.weather.gov/alerts/active?area=WA"  # All active WA alerts, filter for Snohomish
STEVENS_PASS_URL = "https://wsdot.com/Travel/Real-time/mountainpasses/Stevens"  # Scrape for road conditions

async def get_weather_data():
    async with httpx.AsyncClient(headers={"User-Agent": "ThreatDashboard/1.0 (your.email@example.com)"}) as client:
        try:
            # Get point data for forecast
            point_resp = await client.get(POINTS_URL, timeout=10.0)
            point_resp.raise_for_status()
            point_data = point_resp.json()
            forecast_url = point_data["properties"]["forecast"]
            observation_stations = point_data["properties"]["observationStations"]

            # Current conditions from closest station
            obs_resp = await client.get(OBSERVATION_URL, timeout=10.0)
            obs_resp.raise_for_status()
            obs = obs_resp.json()["properties"]

            current_temp = obs["temperature"]["value"]
            current_temp_f = round(current_temp * 1.8 + 32) if current_temp is not None else "N/A"
            conditions = obs["textDescription"] or "Unknown"
            wind_speed = obs["windSpeed"]["value"] or 0
            wind_dir = obs["windDirection"]["value"] or 0
            precip = obs.get("precipitationLastHour", {}).get("value", 0) or 0

            # Forecast for icon (first period)
            forecast_resp = await client.get(forecast_url, timeout=10.0)
            forecast_resp.raise_for_status()
            forecast = forecast_resp.json()["properties"]["periods"][0]
            icon_url = forecast["icon"]

            # Active alerts for Snohomish County / Puget Sound
            alerts_resp = await client.get(ALERTS_URL, timeout=10.0)
            alerts_resp.raise_for_status()
            alerts = alerts_resp.json()["features"]
            relevant_alerts = []
            severe_alert = False
            for alert in alerts:
                props = alert["properties"]
                area = props["areaDesc"]
                if "Snohomish" in area or "King" in area or "Puget Sound" in area:
                    relevant_alerts.append(props["headline"])
                    if props["severity"] in ["Severe", "Extreme"]:
                        severe_alert = True

            # Stevens Pass road conditions (scrape simple text)
            stevens_resp = await client.get(STEVENS_PASS_URL, timeout=10.0)
            stevens_resp.raise_for_status()
            stevens_text = stevens_resp.text
            conditions_match = re.search(r"Conditions:</strong>(.*?)</p>", stevens_text, re.DOTALL)
            restrictions_match = re.search(r"Restrictions.*?</strong>(.*?)</p>", stevens_text, re.DOTALL)
            stevens_conditions = conditions_match.group(1).strip().replace("<br/>", " ") if conditions_match else "Unknown"
            stevens_restrictions = restrictions_match.group(1).strip() if restrictions_match else "None"

            return {
                "current_temp": current_temp_f,
                "conditions": conditions,
                "wind": f"{wind_speed:.0f} mph from {wind_dir}°" if wind_speed else "Calm",
                "precip": precip,
                "icon_url": icon_url,
                "alerts": relevant_alerts,
                "severe_alert": severe_alert,
                "stevens_conditions": stevens_conditions,
                "stevens_restrictions": stevens_restrictions,
                "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Weather API error: {e}")
            return {"error": str(e)}
