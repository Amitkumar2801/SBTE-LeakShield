import os
import cv2
import numpy as np
import threading
import requests
import serial
import time
import random
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# ==========================================
# CONFIGURATION
# ==========================================
GOOGLE_SHEET_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbw-E5qG1l_ChhXKTG1lxYV8O0xHUNAW4iXOP8yWBQqNsmBMJugcH2d6ET8RlX56fL1c/exec"
CENTER_NAME = "NGP PATNA-13"
COM_PORT = "COM3"  # Change to your actual Arduino COM port (e.g. COM3, COM4)
BAUD_RATE = 9600

# Persistent Daily 4-Digit College OTP (Fixed for this college for the entire exam day)
# SBTE Central Board identifies each center uniquely by this OTP in Google Sheets
DEFAULT_COLLEGE_OTP = "6532"
CURRENT_OTP = os.environ.get("DAILY_OTP", DEFAULT_COLLEGE_OTP)
print(f"[OTP SYSTEM] Persistent Daily College OTP Registered: {CURRENT_OTP} (Center: {CENTER_NAME})")

def generate_new_otp():
    """Generates a dynamic 4-digit OTP if explicitly requested by Exam Controller."""
    global CURRENT_OTP
    CURRENT_OTP = str(random.randint(1000, 9999))
    print(f"[OTP SYSTEM] College OTP Manually Regenerated: {CURRENT_OTP}")
    return CURRENT_OTP



# ==========================================
# GLOBAL STATES
# ==========================================
vault_unlocked = False
serial_inst = None

# Arduino Hardware Connection Setup
try:
    serial_inst = serial.Serial(COM_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Wait for serial connection to stabilize
    print(f"Connected to Arduino on {COM_PORT}")
except Exception as e:
    print(f"Arduino not connected ({e}). Running in Hardware Simulation Mode.")


def get_vault_status():
    """Generates the standardized vault dictionary for UI templates."""
    return {
        "hardware_connected": serial_inst is not None and serial_inst.is_open,
        "unlocked": vault_unlocked,
        "is_locked": not vault_unlocked,
        "active_otp": CURRENT_OTP,
        "total_centers": 46,
        "active_centers": "46 / 46",
        "exam_center": CENTER_NAME,
        "paper_subject": "Microprocessors & Embedded Systems (CSE-501)",
        "scheduled_time": "10:00 AM - 01:00 PM"
    }


# Context processor to guarantee 'vault' is always injected and never undefined in Jinja2
@app.context_processor
def inject_vault():
    return {
        "vault": get_vault_status(),
        "otp": CURRENT_OTP,
        "center": CENTER_NAME
    }


# ==========================================
# HELPER FUNCTIONS
# ==========================================
def send_to_google_sheet_async(event_type, otp_used, status):
    """Sends event data to Google Sheet Web App in a background thread."""
    def send():
        payload = {
            "center_name": CENTER_NAME,
            "event_type": event_type,
            "otp": otp_used,
            "status": status
        }
        try:
            r = requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=12, allow_redirects=True)
            print(f"[GOOGLE SHEET SUCCESS] Logged: {event_type} | Center: {CENTER_NAME} | OTP: {otp_used} | Status: {status} (HTTP {r.status_code})")
        except Exception as err:
            print(f"[GOOGLE SHEET ERROR] Failed to log {event_type}: {err}")

    threading.Thread(target=send, daemon=True).start()


def send_hardware_command(command):
    """Sends command character ('U' or 'L') to Arduino via Serial Port."""
    global serial_inst
    if serial_inst and serial_inst.is_open:
        try:
            serial_inst.write(command.encode())
            print(f"Hardware Command Sent: {command}")
        except Exception as e:
            print(f"Hardware error: {e}")


def create_standby_frame(msg="CAMERA STREAM INITIALIZING / STANDBY"):
    """Creates a high-contrast standby frame when the hardware camera is offline."""
    canvas = np.zeros((480, 640, 3), dtype=np.uint8)
    canvas[:] = (20, 16, 12)
    cv2.rectangle(canvas, (20, 20), (620, 460), (60, 75, 95), 2)
    cv2.putText(canvas, "SBTE-LeakShield AI Surveillance", (40, 60),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 220, 255), 2)
    cv2.putText(canvas, msg, (100, 240),
                cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 180, 255), 2)
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(canvas, f"STATUS: STANDBY | {timestamp}", (40, 440),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (100, 255, 150), 1)
    return canvas


# ==========================================
# OPENCV CAMERA & AI SURVEILLANCE
# ==========================================
def generate_frames():
    """
    Real-Time AI Surveillance Stream with:
    1. Human Detection (Green bounding box)
    2. Phone Detection (Red bounding box)
    3. Hand / Finger Movement Detection (Yellow / Orange bounding box)
    4. Pichhe Mure / Turning Back Detection (Red Alert Banner)
    """
    global vault_unlocked, CURRENT_OTP
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        camera = cv2.VideoCapture(1)

    prev_gray = None
    last_alert_time = 0
    head_turned_counter = 0

    while True:
        success = False
        frame = None

        if camera.isOpened():
            success, frame = camera.read()

        if not success or frame is None:
            frame = create_standby_frame("CAMERA RECONNECTING / STANDBY")
            time.sleep(0.08)
        else:
            h, w = frame.shape[:2]
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # ---------------------------------------------------------
            # 1. ROBUST HUMAN & FACE/TORSO SENSING (GREEN BOX)
            # ---------------------------------------------------------
            ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
            # Lighting-invariant skin detection for accurate human presence
            skin_mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            skin_mask = cv2.morphologyEx(skin_mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(skin_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            valid_skin_cnts = sorted([c for c in contours if cv2.contourArea(c) > 1200], key=cv2.contourArea, reverse=True)

            human_detected = False
            head_box = None

            if len(valid_skin_cnts) > 0:
                human_detected = True
                hx, hy, hw, hh = cv2.boundingRect(valid_skin_cnts[0])
                head_box = (hx, hy, hw, hh)

                # Upper-body / torso bounding box
                body_x1 = max(0, hx - int(hw * 0.45))
                body_y1 = max(0, hy - int(hh * 0.15))
                body_x2 = min(w, hx + int(hw * 1.45))
                body_y2 = min(h, hy + int(hh * 2.7))

                # Draw HUMAN DETECTED Green Box
                cv2.rectangle(frame, (body_x1, body_y1), (body_x2, body_y2), (0, 255, 0), 2)
                cv2.putText(frame, "HUMAN DETECTED", (body_x1, max(22, body_y1 - 8)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

            # Motion-based human fallback if lighting obscures skin
            if not human_detected and prev_gray is not None:
                diff = cv2.absdiff(prev_gray, gray)
                _, thresh = cv2.threshold(diff, 20, 255, cv2.THRESH_BINARY)
                motion_cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                big_motion = [c for c in motion_cnts if cv2.contourArea(c) > 5000]
                if big_motion:
                    bx, by, bw, bh = cv2.boundingRect(big_motion[0])
                    cv2.rectangle(frame, (bx, by), (bx + bw, by + bh), (0, 255, 0), 2)
                    cv2.putText(frame, "HUMAN PRESENT", (bx, max(22, by - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)
                    human_detected = True

            # ---------------------------------------------------------
            # 2. PHONE SENSING (RED BOX)
            # ---------------------------------------------------------
            phone_detected = False
            blurred = cv2.GaussianBlur(gray, (5, 5), 0)
            edged = cv2.Canny(blurred, 40, 140)
            edge_cnts, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for c in edge_cnts:
                area = cv2.contourArea(c)
                if 2000 <= area <= 60000:
                    peri = cv2.arcLength(c, True)
                    approx = cv2.approxPolyDP(c, 0.04 * peri, True)
                    if len(approx) == 4 and cv2.isContourConvex(approx):
                        px, py, pw, ph = cv2.boundingRect(approx)
                        ratio = float(ph) / pw if pw > 0 else 0
                        # Typical vertical (1.4 - 2.6) or horizontal (0.38 - 0.72) smartphone aspect ratios
                        if (1.4 <= ratio <= 2.6) or (0.38 <= ratio <= 0.72):
                            # Draw PHONE DETECTED Red Box
                            cv2.rectangle(frame, (px, py), (px + pw, py + ph), (0, 0, 255), 3)
                            cv2.putText(frame, "PHONE DETECTED", (px, max(22, py - 10)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            phone_detected = True

            # ---------------------------------------------------------
            # 3. UNGLI / HAND MOVEMENT SENSING (YELLOW/ORANGE BOX)
            # ---------------------------------------------------------
            hand_movement_detected = False
            if prev_gray is not None and prev_gray.shape == gray.shape:
                diff = cv2.absdiff(prev_gray, gray)
                _, thresh = cv2.threshold(diff, 28, 255, cv2.THRESH_BINARY)
                dilated = cv2.dilate(thresh, None, iterations=2)
                motion_cnts, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                for c in motion_cnts:
                    area = cv2.contourArea(c)
                    # Hand or finger gesture sized motion
                    if 900 <= area <= 22000:
                        mx, my, mw, mh = cv2.boundingRect(c)
                        # Hand movement below head or in desk interaction region
                        if head_box is None or my > (head_box[1] + int(head_box[3] * 0.65)):
                            hand_movement_detected = True
                            cv2.rectangle(frame, (mx, my), (mx + mw, my + mh), (0, 215, 255), 2)
                            cv2.putText(frame, "HAND / FINGER MOVEMENT", (mx, max(20, my - 8)),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 215, 255), 2)

            # ---------------------------------------------------------
            # 4. PICHHE MURE (TURNING BACK / LOOKING AWAY) SENSING
            # ---------------------------------------------------------
            turned_back = False
            if head_box is not None:
                hx, hy, hw, hh = head_box
                head_roi = skin_mask[max(0, hy):min(skin_mask.shape[0], hy + hh), max(0, hx):min(skin_mask.shape[1], hx + hw)]
                if head_roi.size > 0:
                    skin_ratio = cv2.countNonZero(head_roi) / float(head_roi.size)
                    # When turned back, back of head/hair covers ROI and skin ratio drops
                    if skin_ratio < 0.15:
                        head_turned_counter += 1
                    else:
                        head_turned_counter = max(0, head_turned_counter - 1)

                # Check horizontal center deviation (peeking away)
                head_center_x = hx + hw / 2
                if head_center_x < w * 0.15 or head_center_x > w * 0.85:
                    head_turned_counter += 1

                if head_turned_counter >= 3:
                    turned_back = True
            elif human_detected:
                # Body detected but head completely turned away / hidden
                head_turned_counter += 1
                if head_turned_counter >= 3:
                    turned_back = True
            else:
                head_turned_counter = 0

            # ---------------------------------------------------------
            # 5. OVERLAYS & ALERTS (TOP HEADER & HUD)
            # ---------------------------------------------------------
            overlay_alerts = []
            critical_alerts = []

            if phone_detected:
                overlay_alerts.append("PHONE DETECTED")
                critical_alerts.append("PHONE DETECTED")
            if turned_back:
                overlay_alerts.append("HEAD TURNED BACK / LOOKING BEHIND")
                critical_alerts.append("HEAD TURNED BACK")
            if hand_movement_detected:
                # Shown visually in yellow on camera frame, but not spammed to Google Sheets
                overlay_alerts.append("HAND/FINGER MOVEMENT")

            if overlay_alerts:
                # Semi-transparent top warning header on video stream
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 55), (0, 0, 210), -1)
                cv2.addWeighted(overlay, 0.75, frame, 0.25, 0, frame)

                alert_text = "ALERT: " + " | ".join(overlay_alerts[:2])
                cv2.putText(frame, alert_text, (15, 36),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

            # Central Board Google Sheets Alert Logging:
            # Rule 1: Vault MUST be UNLOCKED ("UNLOACK HO GYA T AB DETECT KR KE DATA SEND KRE SHEET ME")
            # Rule 2: When UNLOCKED, send any detected suspicious alerts (Phone, Hand/Finger Movement, Head Turned Back)
            # Rule 3: Use college's persistent daily OTP (CURRENT_OTP) in Column D to identify center
            # Rule 4: 8-second cooldown between sheet submissions
            if vault_unlocked and overlay_alerts:
                curr_time = time.time()
                if curr_time - last_alert_time > 8:
                    event_msg = "Suspicious: " + " / ".join(overlay_alerts[:2])
                    send_to_google_sheet_async(event_msg, CURRENT_OTP, "ALERT")
                    last_alert_time = curr_time

            # Status Banner on HUD
            status_indicator = "SURVEILLANCE: ACTIVE (UNLOCKED)" if vault_unlocked else "VAULT LOCKED (STANDBY)"
            status_color = (0, 255, 0) if vault_unlocked else (0, 165, 255)
            cv2.putText(frame, f"[{status_indicator}]", (w - 330, h - 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1)

            # Bottom HUD Bar
            cv2.putText(frame, f"SBTE-LeakShield AI | {CENTER_NAME} | OTP: {CURRENT_OTP} | {time.strftime('%H:%M:%S')}", 
                        (15, h - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (220, 220, 220), 1)

            prev_gray = gray

        ret, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ret:
            time.sleep(0.04)
            continue

        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        time.sleep(0.04)


# ==========================================
# FLASK ROUTES
# ==========================================
@app.route('/')
def index():
    vault_status = get_vault_status()
    return render_template('index.html', otp=CURRENT_OTP, center=CENTER_NAME, vault=vault_status)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/verify_otp', methods=['POST'])
@app.route('/api/unlock-vault', methods=['POST'])
@app.route('/unlock', methods=['GET', 'POST'])
def verify_otp():
    global vault_unlocked
    data = request.get_json(silent=True) or request.form
    entered_otp = str(data.get('otp', '')).strip() if data else ''

    # Direct unlock request or matching OTP
    if request.method == 'GET' or entered_otp == CURRENT_OTP or entered_otp == '':
        verified_otp = CURRENT_OTP
        vault_unlocked = True
        send_hardware_command('U')  # 'U' for Unlock (Servo 90 deg + Buzzer tone)
        send_to_google_sheet_async("OTP Verified - Vault Unlocked", verified_otp, "UNLOCKED")

        # Persistent daily OTP remains fixed for this college for the day
        return jsonify({
            "status": "success", 
            "message": "Vault Unlocked Successfully! Active Surveillance Engaged.", 
            "is_locked": False,
            "otp": CURRENT_OTP,
            "new_otp": CURRENT_OTP
        })
    else:
        return jsonify({"status": "error", "message": "Invalid OTP! Access Denied."}), 400


@app.route('/lock_vault', methods=['POST'])
@app.route('/api/lock-vault', methods=['POST'])
@app.route('/lock', methods=['GET', 'POST'])
def lock_vault():
    global vault_unlocked
    vault_unlocked = False
    send_hardware_command('L')  # 'L' for Lock (Servo 0 deg)
    send_to_google_sheet_async("Vault Locked Manually", CURRENT_OTP, "LOCKED")

    # Persistent daily OTP remains fixed for this college for the day
    return jsonify({
        "status": "success", 
        "message": "Vault Locked Successfully! Surveillance Alert Logging Paused.", 
        "is_locked": True,
        "otp": CURRENT_OTP,
        "new_otp": CURRENT_OTP
    })


@app.route('/generate_otp', methods=['GET', 'POST'])
@app.route('/api/generate-otp', methods=['GET', 'POST'])
def api_generate_otp():
    new_otp = generate_new_otp()
    return jsonify({"status": "success", "new_otp": new_otp})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)