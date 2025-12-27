import cv2
import time
from datetime import datetime
import os
import pytz

PACIFIC_TZ = pytz.timezone("America/Los_Angeles")

# Sensitivity settings — adjust these
SENSITIVITY_THRESHOLD = 500      # Area in pixels (higher = less sensitive)
MIN_CONTOURS = 3                 # Require at least this many large contours to trigger
BLUR_KERNEL = (21, 21)           # Larger blur = less noise sensitivity
THRESHOLD_VALUE = 25             # Pixel difference threshold

RTSP_URL = "rtsp://admin:Tkinney1@10.0.0.210/cam/realmonitor?channel=1&subtype=0"
SNAPSHOT_PATH = "static/last_motion.jpg"

last_motion_time = None

def detect_motion():
    global last_motion_time

    cap = cv2.VideoCapture(RTSP_URL)

    if not cap.isOpened():
        print("Error: Could not open camera stream")
        return "Camera connection failed"

    print("Connecting to camera:", RTSP_URL)

    # Read first frame
    ret, frame1 = cap.read()
    if not ret:
        cap.release()
        return "Failed to read frame"
    print("First frame captured")
    time.sleep(1)

    # Read second frame
    ret, frame2 = cap.read()
    if not ret:
        cap.release()
        return "Failed to read second frame"
    print("Second frame captured")

    # Preprocess for better noise rejection
    diff = cv2.absdiff(frame1, frame2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
    _, thresh = cv2.threshold(blur, THRESHOLD_VALUE, 255, cv2.THRESH_BINARY)
    dilated = cv2.dilate(thresh, None, iterations=3)
    contours, _ = cv2.findContours(dilated, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    large_contours = 0
    for contour in contours:
        area = cv2.contourArea(contour)
        if area > SENSITIVITY_THRESHOLD:
            large_contours += 1

    print(f"Contours: {len(contours)}, Large (>{SENSITIVITY_THRESHOLD}): {large_contours}")

    cap.release()

    if large_contours >= MIN_CONTOURS:
        cv2.imwrite(SNAPSHOT_PATH, frame2)
        print(f"*** MOTION DETECTED *** at {datetime.now(PACIFIC_TZ).strftime('%H:%M:%S')} ({large_contours} large contours)")
        print(f"Snapshot saved: {SNAPSHOT_PATH}")
        last_motion_time = datetime.now(PACIFIC_TZ)
        return last_motion_time

    return last_motion_time
