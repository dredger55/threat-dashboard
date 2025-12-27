import cv2
import os
from dotenv import load_dotenv

load_dotenv()

RTSP_URL = os.getenv("CAMERA_RTSP")

# Force TCP transport (critical for Dahua reliability)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

print(f"Testing connection to: {RTSP_URL}")

cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

if not cap.isOpened():
    print("ERROR: Failed to open camera stream")
    exit()

cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

print("Camera opened successfully!")

for i in range(10):  # Try to read 10 frames
    ret, frame = cap.read()
    if ret:
        print(f"Frame {i+1} read successfully! Size: {frame.shape}")
    else:
        print(f"Failed to read frame {i+1}")
        
cap.release()
print("Test complete")
