from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
import pytz
import os
from app.camera import detect_motion
from app.traffic import get_traffic_data
from app.weather import get_weather_data
from app.earthquake import get_earthquake_data
from app.crime import get_crime_data
from app.hazard import get_hazard_data
from app.geopolitical import get_geopolitical_data
from app.security import verify_credentials  # <-- NEW: authentication
import logging

logging.basicConfig(level=logging.INFO)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user: str = Depends(verify_credentials)):
    now = datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "title": "Threat Assessment Dashboard", "now": now}
    )

@app.get("/motion-status", response_class=HTMLResponse)
async def motion_status(user: str = Depends(verify_credentials)):
    logging.info("=== Motion status requested ===")
    last_motion = detect_motion()
    now = datetime.now(PACIFIC_TZ)

    if isinstance(last_motion, str):
        status = last_motion
        color = "orange"
        image_html = ""
    elif last_motion is None:
        status = "No recent motion detected"
        color = "#00ff00"
        image_html = ""
    else:
        delta = now - last_motion
        if delta < timedelta(minutes=5):
            status = f"MOTION DETECTED {int(delta.total_seconds())} seconds ago!"
            color = "red"
            ts = int(now.timestamp())
            image_html = f'''
            <div id="snapshot-container" hx-get="/snapshot" hx-trigger="every 5s" hx-swap="outerHTML">
                <img src="/static/last_motion.jpg?t={ts}" style="max-width:100%; border-radius:8px; margin-top:10px;">
            </div>
            '''
        else:
            status = f"Last motion: {int(delta.total_seconds() // 60)} minutes ago"
            color = "#ffff00"
            if os.path.exists("static/last_motion.jpg"):
                ts = int(os.path.getmtime("static/last_motion.jpg"))
                image_html = f'<img src="/static/last_motion.jpg?t={ts}" style="max-width:100%; border-radius:8px; margin-top:10px;">'
            else:
                image_html = ""

    return f"""
    <div class="card" hx-get="/motion-status" hx-trigger="load, every 30s" hx-swap="outerHTML">
        <h2>Front Door Camera (Motion Detection)</h2>
        <div class="card-content">
            <p id="motion-status" style="color:{color}; font-weight:bold;">{status}</p>
            <p>Last check: <span id="motion-time">{now.strftime("%H:%M:%S")}</span></p>
        </div>
        {image_html}
    </div>
    """

@app.get("/snapshot", response_class=HTMLResponse)
async def snapshot(user: str = Depends(verify_credentials)):
    snapshot_path = "static/last_motion.jpg"
    if os.path.exists(snapshot_path):
        ts = int(os.path.getmtime(snapshot_path))
        return f'''
        <div id="snapshot-container" hx-get="/snapshot" hx-trigger="every 5s" hx-swap="outerHTML">
            <img src="/static/last_motion.jpg?t={ts}" style="max-width:100%; border-radius:8px; margin-top:10px;">
        </div>
        '''
    else:
        return '<div id="snapshot-container"></div>'

@app.get("/traffic-status", response_class=HTMLResponse)
async def traffic_status(user: str = Depends(verify_credentials)):
    data = await get_traffic_data()

    if "error" in data:
        content = f"<div class='card-content'><p style='color:orange;'>Traffic API error: {data['error']}</p></div>"
        dot_color = "orange"
    else:
        def format_incidents(incidents):
            if not incidents:
                return "<span style='color:#00ff00;'>No incidents reported</span>"
            lines = []
            for inc in incidents:
                cat = inc.get("EventCategory", "Alert")
                desc = inc.get("HeadlineDescription", "Unknown incident")
                start = inc.get("StartTime", "")
                lines.append(f"<strong>{cat} ({start}):</strong> {desc}")
            return "<br>".join(lines[:10])

        highway2_text = format_incidents(data["highway2_incidents"])
        highway522_text = format_incidents(data["highway522_incidents"])

        content = f"""
        <div class="card-content">
            <div class="vertical-marquee">
                <div class="vertical-marquee-content">
                    <p><strong>{data["highway2"]}:</strong><br>{highway2_text}</p>
                    <p><strong>{data["highway522"]}:</strong><br>{highway522_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data.get("last_update", "-")}</p>
                </div>
                <div class="vertical-marquee-content duplicate">
                    <p><strong>{data["highway2"]}:</strong><br>{highway2_text}</p>
                    <p><strong>{data["highway522"]}:</strong><br>{highway522_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data.get("last_update", "-")}</p>
                </div>
            </div>
        </div>
        """

        dot_color = data.get("congestion_color", "#00ff00")

    return f"""
    <div class="card" hx-get="/traffic-status" hx-trigger="load, every 120s" hx-swap="outerHTML">
        <h2>Traffic Incidents <span style="font-size:1.5em; color:{dot_color}">●</span></h2>
        {content}
    </div>
    """

@app.get("/weather-status", response_class=HTMLResponse)
async def weather_status(user: str = Depends(verify_credentials)):
    data = await get_weather_data()

    if "error" in data:
        content = f"<div class='card-content'><p style='color:orange;'>Weather API error: {data['error']}</p></div>"
    else:
        alerts_text = "<br>".join(data["alerts"]) if data["alerts"] else "<span style='color:#00ff00;'>No active alerts</span>"
        content = f"""
        <div class="card-content">
            <div class="vertical-marquee">
                <div class="vertical-marquee-content">
                    <p><strong>Monroe:</strong> {data["current_temp"]}°F, {data["conditions"]}<br>
                    Wind: {data["wind"]}, Precip last hour: {data["precip"]:.2f}\"</p>
                    <p><strong>Stevens Pass:</strong><br>Conditions: {data["stevens_conditions"]}<br>
                    Restrictions: {data["stevens_restrictions"]}</p>
                    <p><strong>Alerts:</strong><br>{alerts_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
                <div class="vertical-marquee-content duplicate">
                    <p><strong>Monroe:</strong> {data["current_temp"]}°F, {data["conditions"]}<br>
                    Wind: {data["wind"]}, Precip last hour: {data["precip"]:.2f}\"</p>
                    <p><strong>Stevens Pass:</strong><br>Conditions: {data["stevens_conditions"]}<br>
                    Restrictions: {data["stevens_restrictions"]}</p>
                    <p><strong>Alerts:</strong><br>{alerts_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
            </div>
        </div>
        """

    return f"""
    <div class="card" hx-get="/weather-status" hx-trigger="load, every 300s" hx-swap="outerHTML">
        <h2>Weather</h2>
        {content}
    </div>
    """

@app.get("/earthquake-status", response_class=HTMLResponse)
async def earthquake_status(user: str = Depends(verify_credentials)):
    data = await get_earthquake_data()

    if "error" in data:
        content = f"<div class='card-content'><p style='color:orange;'>Earthquake API error: {data['error']}</p></div>"
    else:
        quakes_text = "<br>".join(data["quakes"]) if data["quakes"] else "<span style='color:#00ff00;'>No recent quakes</span>"
        content = f"""
        <div class="card-content">
            <div class="vertical-marquee">
                <div class="vertical-marquee-content">
                    <p><strong>Recent quakes (Puget Sound region):</strong><br>{quakes_text}</p>
                    <p><strong>Tsunami status:</strong> {data["tsunami"]}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
                <div class="vertical-marquee-content duplicate">
                    <p><strong>Recent quakes (Puget Sound region):</strong><br>{quakes_text}</p>
                    <p><strong>Tsunami status:</strong> {data["tsunami"]}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
            </div>
        </div>
        """

    return f"""
    <div class="card" hx-get="/earthquake-status" hx-trigger="load, every 300s" hx-swap="outerHTML">
        <h2>Earthquakes & Tsunami</h2>
        {content}
    </div>
    """

@app.get("/crime-status", response_class=HTMLResponse)
async def crime_status(user: str = Depends(verify_credentials)):
    data = await get_crime_data()

    if "error" in data:
        content = f"<div class='card-content'><p style='color:orange;'>Crime data error: {data['error']}</p></div>"
    else:
        incidents_text = "<br>".join(data["incidents"]) if data["incidents"] else "<span style='color:#00ff00;'>No recent incidents</span>"
        content = f"""
        <div class="card-content">
            <div class="vertical-marquee">
                <div class="vertical-marquee-content">
                    <p><strong>Recent incidents (within 5 miles):</strong><br>{incidents_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
                <div class="vertical-marquee-content duplicate">
                    <p><strong>Recent incidents (within 5 miles):</strong><br>{incidents_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
            </div>
        </div>
        """

    return f"""
    <div class="card" hx-get="/crime-status" hx-trigger="load, every 600s" hx-swap="outerHTML">
        <h2>Local Crime (within 5 miles)</h2>
        {content}
    </div>
    """

@app.get("/hazard-status", response_class=HTMLResponse)
async def hazard_status(user: str = Depends(verify_credentials)):
    data = await get_hazard_data()

    if "error" in data:
        content = f"<div class='card-content'><p style='color:orange;'>Hazard data error: {data['error']}</p></div>"
    else:
        content = f"""
        <div class="card-content">
            <div class="vertical-marquee">
                <div class="vertical-marquee-content">
                    <p>{data["power"]}</p>
                    <p>{data["gas"]}</p>
                    <p>{data["internet"]}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
                <div class="vertical-marquee-content duplicate">
                    <p>{data["power"]}</p>
                    <p>{data["gas"]}</p>
                    <p>{data["internet"]}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
            </div>
        </div>
        """

    return f"""
    <div class="card" hx-get="/hazard-status" hx-trigger="load, every 600s" hx-swap="outerHTML">
        <h2>Hazard Alerts (Puget Sound Region)</h2>
        {content}
    </div>
    """

@app.get("/geopolitical-status", response_class=HTMLResponse)
async def geopolitical_status(user: str = Depends(verify_credentials)):
    data = await get_geopolitical_data()

    if "error" in data:
        content = f"<div class='card-content'><p style='color:orange;'>Geopolitical data error: {data['error']}</p></div>"
    else:
        events_text = "<br>".join(data["events"])
        content = f"""
        <div class="card-content">
            <div class="vertical-marquee">
                <div class="vertical-marquee-content">
                    <p><strong>Relevant events:</strong><br>{events_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
                <div class="vertical-marquee-content duplicate">
                    <p><strong>Relevant events:</strong><br>{events_text}</p>
                    <p style="font-size:0.8em; color:#aaa;">Last update: {data["last_update"]}</p>
                </div>
            </div>
        </div>
        """

    return f"""
    <div class="card" hx-get="/geopolitical-status" hx-trigger="load, every 900s" hx-swap="outerHTML">
        <h2>Geopolitical (US Northwest)</h2>
        {content}
    </div>
    """

@app.get("/threat-level", response_class=HTMLResponse)
async def threat_level_fragment(user: str = Depends(verify_credentials)):
    active_reasons = []

    last_motion = detect_motion()
    if last_motion and (datetime.now(PACIFIC_TZ) - last_motion) < timedelta(minutes=5):
        active_reasons.append("Front door motion")

    traffic_data = await get_traffic_data()
    if "major_incident" in traffic_data and traffic_data["major_incident"]:
        active_reasons.append("Major traffic incident")

    weather_data = await get_weather_data()
    if "alerts" in weather_data and weather_data["alerts"]:
        active_reasons.append("Weather alerts")

    eq_data = await get_earthquake_data()
    if "major_quake" in eq_data and eq_data["major_quake"]:
        active_reasons.append("Major earthquake or tsunami")

    crime_data = await get_crime_data()
    if "violent_crime" in crime_data and crime_data["violent_crime"]:
        active_reasons.append("Local violent crime")

    hazard_data = await get_hazard_data()
    if "major_outage" in hazard_data and hazard_data["major_outage"]:
        active_reasons.append("Major utility outage")

    geo_data = await get_geopolitical_data()
    if "major_event" in geo_data and geo_data["major_event"]:
        active_reasons.append("Geopolitical threat")

    if len(active_reasons) >= 4:
        level = "SEVERE"
        color = "red"
    elif len(active_reasons) >= 3:
        level = "HIGH"
        color = "orange"
    elif len(active_reasons) >= 1:
        level = "ELEVATED"
        color = "yellow"
    else:
        level = "LOW"
        color = "#00ff00"
        active_reasons = ["All clear"]

    reasons_text = " | ".join(active_reasons)

    return f"""
    <div style="text-align:center; padding:1rem; background:#1a1a2e; border-bottom:3px solid #00ffea;">
        <h1 class="threat-level" style="color:{color}; text-shadow: 0 0 30px {color}; font-size:3rem; margin:0;">
            THREAT LEVEL: <span id="level-text">{level}</span>
        </h1>
        <p>Last updated: {datetime.now(PACIFIC_TZ).strftime("%Y-%m-%d %H:%M:%S %Z")}</p>
        <p id="threat-reasons" style="color:{color};">{reasons_text}</p>
    </div>
    """
