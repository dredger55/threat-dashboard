import httpx
from datetime import datetime
import pytz
import re

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

PUD_URL = "https://outage.snopud.com/"
PSE_URL = "https://www.pse.com/outage/outage-map"
XFINITY_URL = "https://downdetector.com/status/comcast-xfinity/"

async def get_hazard_data():
    async with httpx.AsyncClient() as client:
        try:
            # PUD Electric
            pud_outages = "Status unavailable"
            major_pud = False
            try:
                pud_resp = await client.get(PUD_URL, timeout=15.0)
                if pud_resp.status_code == 200:
                    pud_text = pud_resp.text.lower()
                    if "current outages" in pud_text:
                        match = re.search(r"current outages.*?(\d+)", pud_text)
                        pud_outages = match.group(1) if match else "Unknown"
                    elif "no outages" in pud_text:
                        pud_outages = "0"
                    major_pud = int(pud_outages) > 50 if pud_outages.isdigit() else False
            except Exception as e:
                print(f"PUD error: {e}")

            # PSE Natural Gas
            pse_status = "No gas alerts"
            major_pse = False
            try:
                pse_resp = await client.get(PSE_URL, timeout=15.0)
                if pse_resp.status_code == 200:
                    pse_text = pse_resp.text.lower()
                    if "natural gas" in pse_text or "gas" in pse_text:
                        if "no outages" in pse_text:
                            pse_status = "No gas outages"
                        else:
                            pse_status = "Gas issues reported"
                            major_pse = True
            except Exception as e:
                print(f"PSE error: {e}")

            # Xfinity Internet
            xfinity_status = "No widespread issues"
            major_xfinity = False
            try:
                xfinity_resp = await client.get(XFINITY_URL, timeout=15.0)
                if xfinity_resp.status_code == 200:
                    xfinity_text = xfinity_resp.text.lower()
                    if "no problems" in xfinity_text:
                        xfinity_status = "No widespread issues"
                    else:
                        xfinity_status = "Possible issues reported"
                        major_xfinity = True
            except Exception as e:
                print(f"Xfinity error: {e}")

            major_outage = major_pud or major_pse or major_xfinity

            return {
                "power": f"PUD Electric: {pud_outages} customers affected",
                "gas": f"PSE Natural Gas: {pse_status}",
                "internet": f"Xfinity Internet: {xfinity_status}",
                "major_outage": major_outage,
                "last_update": datetime.now(PACIFIC_TZ).strftime("%H:%M:%S")
            }
        except Exception as e:
            print(f"Hazard alert error: {e}")
            return {"error": str(e)}
