# Threat Assessment Dashboard

A self-hosted, cyberpunk-style real-time threat monitoring dashboard built with FastAPI and HTMX.

## Features

- Real-time threat level calculation
- Front door motion detection with snapshot
- Traffic incidents (Highway 2 & Highway 522)
- Weather alerts & Stevens Pass conditions
- Earthquake & tsunami status
- Local crime reports (within 5 miles)
- Utility outage alerts
- Geopolitical events
- Secure Basic Authentication
- Smooth vertical scrolling cards

## Prerequisites

- Ubuntu server
- Python 3.12+
- Internet access for APIs

## Quick Start

```bash
git clone https://github.com/dredger55/threat-dashboard.git
cd threat-dashboard
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx pytz "passlib[bcrypt]" opencv-python
uvicorn app.main:app --host 0.0.0.0 --port 80
