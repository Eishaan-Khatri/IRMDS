import cv2
from ultralytics import YOLO
import time
import json
from datetime import datetime

model = YOLO('yolov8n.pt')
cap = cv2.VideoCapture(0)

# Config
ALERT_THRESHOLD = 0  # alert if more than 0 people detected
LOG_FILE = "detections.json"
logs = []
COOLDOWN_SECONDS = 10  # only alert once every 10 seconds
last_alert_time = 0

def log_event(event_type, details):
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": event_type,
        "details": details
    }
    logs.append(entry)
    with open(LOG_FILE, "w") as f:
        json.dump(logs, f, indent=2)
    print(f"[ALERT] {entry}")

frame_count = 0
start_time = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model(frame, verbose=False)
    detections = results[0].boxes
    annotated = results[0].plot()

    # Count people
    people = [d for d in detections if int(d.cls[0]) == 0]
    count = len(people)

    # FPS calculation
    frame_count += 1
    elapsed = time.time() - start_time
    fps = frame_count / elapsed

    '''# Anomaly detection logic
    if count > ALERT_THRESHOLD:
        log_event("CROWD_ANOMALY", {"person_count": count})'''

    # Overlay stats on frame
    cv2.putText(annotated, f"People: {count}", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(annotated, f"FPS: {fps:.1f}", (10, 65),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
    cv2.putText(annotated, f"Latency: {results[0].speed['inference']:.1f}ms", (10, 100),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    current_time = time.time()
    if count >= ALERT_THRESHOLD and (current_time - last_alert_time) > COOLDOWN_SECONDS:
        log_event("CROWD_ANOMALY", {"person_count": count})
        last_alert_time = current_time  

    cv2.imshow('IRMDS - Module 1', annotated)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
print(f"\nSession complete. {len(logs)} events logged to {LOG_FILE}")