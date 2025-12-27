import httpx
from datetime import datetime
import pytz
import xml.etree.ElementTree as ET

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

# Updated DHS NTAS RSS (current location)
NTAS_RSS = "https://www.dhs.gov/ntas/rss.xml"

# NWS CAP feed for Washington state
NWS_CAP = "https://alerts.weather.gov/cap/wa.php?x=1"

async def get_geopolitical_data():
    async with httpx.AsyncClient() as client:
        try:
            events = []
            major_event = False

            # DHS NTAS bulletins
            try:
                ntas_resp = await client.get(NTAS_RSS, timeout=15.0)
                if ntas_resp.status_code == 200:
                    ntas_root = ET.fromstring(ntas_resp.content)
                    for item in ntas_root.findall(".//item"):
                        title = item.find("title").text if item.find("title") is not None else "NTAS Bulletin"
                        description = item.find("description").text if item.find("description") is not None else ""
                        pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                        events.append(f"<strong>DHS NTAS:</strong> {title}")
                        major_event = True
            except Exception as e:
                print(f"NTAS error: {e}")

            # Washington state non-weather emergency alerts
            try:
                cap_resp = await client.get(NWS_CAP, timeout=15.0)
                if cap_resp.status_code == 200:
                    cap_root = ET.fromstring(cap_resp.content)
                    for entry in cap_root.findall(".//{http://www.w3.org/2005/Atom}entry"):
                        event_elem = entry.find(".//{urn:oasis:names:tc:emergency:cap:1.2}event")
                        if event_elem is not None:
                            event_text = event_elem.text.lower()
                            if "weather" not in event_text and "snow" not in event_text and "rain" not in event_text:
                                title = entry.find("{http://www.w3.org/2005/Atom}title").text if entry.find("{http://www.w3.org/2005/Atom}title") is not None else "State Alert"
                                events.append(f"<strong>WA Emergency:</strong> {title}")
                                major_event = True
            except Exception as e:
                print(f"CAP error: {e}")

            if not events:
                events.append("<span style='color:#00ff00;'>No major geopolitical events</span>")

            return {
                "events": events,
                "major_event": major_event,
                "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Geopolitical error: {e}")
            return {"error": str(e)}
