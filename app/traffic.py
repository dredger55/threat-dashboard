import httpx
from datetime import datetime, timedelta
import pytz

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

ACCESS_CODE = "573baea1-57ec-4cd7-9532-43c89b8bb4b0"

ALERTS_URL = f"https://wsdot.wa.gov/Traffic/api/HighwayAlerts/HighwayAlertsREST.svc/GetAlertsAsJson?AccessCode={ACCESS_CODE}"

first_load = True

async def get_traffic_data():
    global first_load

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(ALERTS_URL, timeout=15.0)
            resp.raise_for_status()
            alerts = resp.json()

            now = datetime.now(PACIFIC_TZ)
            cutoff = now - timedelta(days=14 if first_load else 0)

            highway2_incidents = []
            highway522_incidents = []
            major_incident = False

            for alert in alerts:
                start_time_str = alert.get("StartTime", "")
                try:
                    start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00")).astimezone(PACIFIC_TZ)
                except:
                    start_time = now

                if start_time < cutoff:
                    continue

                headline = alert.get("HeadlineDescription", "Unknown incident").lower()
                category = alert.get("EventCategory", "Alert")
                priority = alert.get("Priority", "Low")

                # Major incident detection
                if priority in ["High", "Highest"] or any(word in headline for word in ["closure", "blocked", "crash", "accident"]):
                    major_incident = True

                incident = {
                    "HeadlineDescription": alert.get("HeadlineDescription", "Unknown incident"),
                    "EventCategory": category,
                    "Priority": priority,
                    "StartTime": start_time.strftime("%m/%d %H:%M")
                }

                # ONLY Highway 2 / SR 2 / US 2
                if any(keyword in headline for keyword in ["sr 2", "us 2", "highway 2", "sr2", "us2", "sr-2", "us-2"]):
                    highway2_incidents.append(incident)

                # ONLY Highway 522 / SR 522
                if any(keyword in headline for keyword in ["sr 522", "highway 522", "sr522", "sr-522"]):
                    highway522_incidents.append(incident)

            highway2_incidents.sort(key=lambda x: x.get("StartTime", ""), reverse=True)
            highway522_incidents.sort(key=lambda x: x.get("StartTime", ""), reverse=True)

            if first_load:
                first_load = False

            last_update = now.strftime("%H:%M:%S")

            return {
                "highway2": "Highway 2 (Everett → Wenatchee)",
                "highway2_incidents": highway2_incidents[:10],
                "highway522": "Highway 522 (Monroe → Seattle)",
                "highway522_incidents": highway522_incidents[:10],
                "major_incident": major_incident,
                "congestion_color": "#ff0000" if major_incident else "#00ff00",
                "last_update": last_update
            }

        except Exception as e:
            print(f"Traffic API error: {e}")
            return {"error": str(e)}
