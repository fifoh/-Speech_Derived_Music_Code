# ---------------------
# This script is for overlaying subtitles on the live video stream.
# ---------------------

from picamera2 import Picamera2
import cv2, numpy as np, os

# ---------------------
# Setup camera
# ---------------------
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration(
    main={"size": (1280, 720), "format": "YUV420"}
)
picam2.configure(camera_config)
picam2.set_controls({"FrameRate": 20, "AwbEnable": True})
picam2.start()

# ---------------------
# OpenCV window
# ---------------------
cv2.namedWindow("Camera Overlay", cv2.WINDOW_NORMAL)
cv2.setWindowProperty("Camera Overlay", cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

# ---------------------
# Overlay setup
# ---------------------
font = cv2.FONT_HERSHEY_SIMPLEX
font_scale, thickness = 2, 3
color = (255, 255, 255)
word, last_mtime, overlay = "", 0, None

# ---------------------
# Main loop
# ---------------------
while True:
    # Capture YUV and convert to BGR
    frame = picam2.capture_array("main")
    frame = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)

    # Only read text file when changed
    try:
        mtime = os.path.getmtime("/tmp/current_word.txt")
        if mtime != last_mtime:
            with open("/tmp/current_word.txt") as f:
                word = f.read().strip()
            last_mtime = mtime

            overlay = np.zeros_like(frame)
            if word:
                (tw, th), _ = cv2.getTextSize(word, font, font_scale, thickness)
                x, y = (frame.shape[1] - tw)//2, frame.shape[0] - 90
                cv2.putText(overlay, word, (x, y), font, font_scale, color, thickness)
    except FileNotFoundError:
        word, overlay = "", None

    if overlay is not None:
        cv2.addWeighted(overlay, 1, frame, 1, 0, frame)

    cv2.imshow("Camera Overlay", frame)

    if cv2.waitKey(1) & 0xFF == 27:
        break

cv2.destroyAllWindows()
picam2.stop()

