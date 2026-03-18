# IRMDS — Intelligent Real-Time Monitoring & Decision System

A modular, production-grade AI pipeline for real-time anomaly detection across visual, network, and time-series domains.

## Architecture
```
Video Input → YOLOv8 Inference → Anomaly Logic → Cooldown Filter → JSON Event Log
```

## Current Modules

### Module 1 — Visual Anomaly Detection (Live)
- Real-time person detection via YOLOv8n
- Configurable threshold-based anomaly triggering
- Production-style cooldown system (prevents alert storms)
- JSON structured event logging with timestamps
- Live FPS + latency overlay

**Performance (CPU):** ~13 FPS | ~70ms inference latency

## Roadmap
- [ ] Module 2 — Network/Time-Series Anomaly Detection
- [ ] FastAPI REST backend
- [ ] WebSocket real-time streaming
- [ ] Docker containerization
- [ ] Unified dashboard (Streamlit/Grafana)

## Tech Stack
- Python, OpenCV, YOLOv8 (Ultralytics)
- FastAPI (coming)
- Docker (coming)

## Quick Start
```bash
pip install opencv-python ultralytics fastapi uvicorn
python project_0.py
```

## Why This Project
Most AI projects stop at model accuracy. IRMDS is built around systems concerns:
latency, alert reliability, modular deployment, and real-world pipeline design.