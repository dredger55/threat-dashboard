import httpx
from datetime import datetime
import pytz
import re
import json

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

ZIP_CODE = "98272"

CRIME_URL = f"https://communitycrimemap.com/?address={ZIP_CODE}&radius=5&days=30"

async def get_crime_data():
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(CRIME_URL, timeout=15.0)
            resp.raise_for_status()
            text = resp.text

            match = re.search(r"var markers = (\[.*?\]);", text, re.DOTALL)
            if not match:
                return {
                    "incidents": ["<span style='color:#00ff00;'>No recent incidents reported</span>"],
                    "violent_crime": False,
                    "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
                }

            markers = json.loads(match.group(1))

            incidents = []
            violent_crime = False

            for marker in markers[:10]:
                desc = marker.get("description", "Unknown incident")
                date_str = marker.get("date", "Unknown date")
                crime_type = marker.get("type", "Unknown")

                if any(word in crime_type.lower() for word in ["assault", "robbery", "homicide", "weapon"]):
                    violent_crime = True
                    style = "color:red; font-weight:bold;"
                else:
                    style = ""

                incidents.append(f'<span style="{style}">{date_str} | {crime_type} | {desc}</span>')

            if not incidents:
                incidents = ["<span style='color:#00ff00;'>No recent incidents reported</span>"]

            return {
                "incidents": incidents,
                "violent_crime": violent_crime,
                "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Crime API error: {e}")
            return {
                "incidents": [f"<span style='color:orange;'>Crime data unavailable: {str(e)}</span>"],
                "violent_crime": False,
                "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
            }
