"""
SBTE-LeakShield: AI Surveillance Engine
Real-Time OpenCV Human Face/Body, Phone & Sudden Rapid Movement Detection
"""

import cv2
import time
import numpy as np


class SurveillanceEngine:
    def __init__(self, camera_source=0):
        self.camera_source = camera_source
        self.cap = None
        self.prev_gray = None
        self.last_motion_time = 0
        self.motion_cooldown = 1.5  # seconds overlay remains active
        self.suspicious_active = False

        # Try initializing Haar cascade if supported by installed OpenCV build
        self.face_cascade = None
        if hasattr(cv2, 'CascadeClassifier') and hasattr(cv2, 'data'):
            try:
                cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
                if self.face_cascade.empty():
                    self.face_cascade = None
            except Exception:
                self.face_cascade = None

    def init_camera(self):
        """Initializes video capture device."""
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_source)
        return self.cap.isOpened()

    def release(self):
        """Releases video capture."""
        if self.cap is not None and self.cap.isOpened():
            self.cap.release()

    def detect_human_face_body(self, frame):
        """
        Detects human face or body regions.
        Uses Haar Cascade if available, and falls back to color/contour segmentation.
        """
        faces = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Method A: Haar Cascade (OpenCV 4.x)
        if self.face_cascade is not None:
            detected = self.face_cascade.detectMultiScale(
                gray,
                scaleFactor=1.1,
                minNeighbors=5,
                minSize=(50, 50)
            )
            for (x, y, w, h) in detected:
                faces.append((x, y, w, h))

        # Method B: Universal Skin/Head Region Segmentation (OpenCV 5.x / fallback)
        if len(faces) == 0:
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([25, 255, 255], dtype=np.uint8)
            mask = cv2.inRange(hsv, lower_skin, upper_skin)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                if cv2.contourArea(c) > 3500:
                    x, y, w, h = cv2.boundingRect(c)
                    ratio = float(h) / w if w > 0 else 0
                    if 0.8 <= ratio <= 2.4:
                        faces.append((x, y, w, h))

        return faces

    def detect_phone(self, frame):
        """
        Detects phone-like handheld objects using edge contour and aspect-ratio analysis.
        Typical handheld smartphone aspect ratio: ~1.5 - 2.5.
        """
        detected_boxes = []
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 60, 180)

        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.04 * peri, True)

            # Approximate 4-sided polygon (quadrilateral)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)
                # Size constraints for a smartphone held up to camera
                if 45 <= w <= 240 and 85 <= h <= 460:
                    aspect_ratio = float(h) / w if w > 0 else 0
                    if 1.5 <= aspect_ratio <= 2.5:
                        detected_boxes.append((x, y, w, h))
        return detected_boxes

    def detect_rapid_movement(self, gray_frame):
        """
        Detects sudden rapid movement by computing absolute frame difference.
        """
        motion_boxes = []
        if self.prev_gray is None:
            self.prev_gray = gray_frame.copy()
            return motion_boxes

        # Absolute difference between consecutive frames
        frame_diff = cv2.absdiff(self.prev_gray, gray_frame)
        self.prev_gray = gray_frame.copy()

        blurred_diff = cv2.GaussianBlur(frame_diff, (21, 21), 0)
        _, thresh = cv2.threshold(blurred_diff, 28, 255, cv2.THRESH_BINARY)
        dilated = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            area = cv2.contourArea(c)
            # High area threshold indicating sudden rapid movement
            if area > 4500:
                x, y, w, h = cv2.boundingRect(c)
                motion_boxes.append((x, y, w, h))

        return motion_boxes

    def process_frame(self, frame):
        """
        Processes a single frame:
        1. Detects human faces/bodies (green box)
        2. Detects phone-like objects or rapid motion (red box)
        3. Overlays 'SUSPICIOUS ACTIVITY' banner if triggered
        """
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        is_suspicious = False
        suspicious_reasons = []

        # 1. Human Face/Body Detection (Normal invigilation in green)
        faces = self.detect_human_face_body(frame)
        for (fx, fy, fw, fh) in faces:
            cv2.rectangle(frame, (fx, fy), (fx + fw, fy + fh), (0, 255, 100), 2)
            cv2.putText(frame, "HUMAN PRESENCE", (fx, max(20, fy - 8)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 100), 1)

        # 2. Phone Detection (Red bounding box)
        phone_boxes = self.detect_phone(frame)
        for (px, py, pw, ph) in phone_boxes:
            is_suspicious = True
            suspicious_reasons.append("PHONE DETECTED")
            cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 0, 255), 3)
            cv2.putText(frame, "PHONE OBJECT", (px, max(20, py - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # 3. Sudden Rapid Movement Detection (Red bounding box)
        motion_boxes = self.detect_rapid_movement(gray)
        for (mx, my, mw, mh) in motion_boxes:
            is_suspicious = True
            suspicious_reasons.append("RAPID MOVEMENT")
            cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (0, 0, 255), 3)
            cv2.putText(frame, "RAPID MOTION", (mx, max(20, my - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        current_time = time.time()
        if is_suspicious:
            self.last_motion_time = current_time

        # Maintain overlay for alert cooldown duration
        if current_time - self.last_motion_time < self.motion_cooldown:
            # Draw semi-transparent top warning header
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, 55), (0, 0, 200), -1)
            cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

            # Display "SUSPICIOUS ACTIVITY" overlay text
            alert_text = "SUSPICIOUS ACTIVITY"
            if suspicious_reasons:
                alert_text += f": {', '.join(set(suspicious_reasons))}"

            cv2.putText(
                frame,
                alert_text,
                (20, 36),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        # Telemetry HUD
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, f"SBTE-LeakShield Vision AI | {timestamp}", (15, h - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 220, 220), 1)

        return frame, is_suspicious


def generate_frames(camera_source=0):
    """
    Generator function used by Flask /video_feed route.
    Yields multipart JPEG frames.
    """
    engine = SurveillanceEngine(camera_source=camera_source)
    opened = engine.init_camera()

    while True:
        if opened and engine.cap is not None and engine.cap.isOpened():
            success, frame = engine.cap.read()
            if not success:
                frame = create_fallback_frame("CAMERA RECONNECTING...")
            else:
                frame, _ = engine.process_frame(frame)
        else:
            frame = create_fallback_frame("CAMERA STANDBY / SIMULATION")

        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            time.sleep(0.04)
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)  # ~25 FPS


def create_fallback_frame(status_msg="NO WEBCAM ATTACHED"):
    """Creates a high-contrast HUD standby frame when hardware camera is offline."""
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    canvas[:] = (20, 16, 12)

    # Border frame
    cv2.rectangle(canvas, (20, 20), (620, 460), (60, 75, 95), 2)
    cv2.putText(canvas, "SBTE-LeakShield Surveillance Feed", (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)

    cv2.putText(canvas, status_msg, (120, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 160, 255), 2)
    cv2.putText(canvas, "Plug in USB camera to activate live optical sensor", (110, 280),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (160, 160, 160), 1)

    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(canvas, f"VISION STATUS: ONLINE | {timestamp}", (40, 440),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 150), 1)
    return canvas


def run_standalone(camera_source=0):
    """Interactive desktop OpenCV window execution."""
    print(f"[*] Starting SBTE-LeakShield AI Surveillance on Camera {camera_source}")
    print("[*] Press 'q' to quit.")
    engine = SurveillanceEngine(camera_source=camera_source)
    if not engine.init_camera():
        print("[!] Error: Could not open camera. Exiting.")
        return

    while True:
        success, frame = engine.cap.read()
        if not success:
            print("[!] Failed to grab frame.")
            break

        processed_frame, _ = engine.process_frame(frame)
        cv2.imshow("SBTE-LeakShield - Real-Time AI Surveillance", processed_frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    engine.release()
    cv2.destroyAllWindows()


if __name__ == '__main__':
    run_standalone()
