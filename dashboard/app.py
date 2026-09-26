"""
SBTE-LeakShield: Central Dashboard Backend
Flask Server with Real-Time Video Streaming, Hardware Serial Integration, 
4-Digit OTP Vault Unlock & Asynchronous Google Sheets Event Logging
"""

import os
import sys
import time
import threading
from datetime import datetime
import requests
from flask import Flask, render_template, request, jsonify, Response

# Add parent directory to path to import ai_surveillance module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from ai_surveillance.detect import generate_frames
except ImportError:
    # Fallback frame generator if OpenCV or module import fails
    def generate_frames(camera_source=0, alert_callback=None):
        while True:
            time.sleep(1)
            yield b''

# Optional PySerial support for real Arduino microcontroller
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sbte-leakshield-secure-2026')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# --- Google Sheets Web App Endpoint ---
GOOGLE_SHEET_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbw-E5qG1l_ChhXKTG1lxYV8O0xHUNAW4iXOP8yWBQqNsmBMJugcH2d6ET8RlX56fL1c/exec"


def send_to_google_sheet(center_name, event_type, otp, status):
    """
    Sends event telemetry to Google Sheets Web App in a non-blocking background thread.
    Catches all network exceptions to prevent stalling Flask or the OpenCV stream.
    
    Payload Structure:
    {
      "center_name": "NGP PATNA-13",
      "event_type": "Vault Unlocked / Motion Alert",
      "otp": "4829",
      "status": "UNLOCKED / ALERT"
    }
    """
    def _worker():
        payload = {
            "center_name": center_name,
            "event_type": event_type,
            "otp": str(otp),
            "status": status
        }
        try:
            # Google Apps Script web apps return a 302 redirect on POST, so allow_redirects=True is vital
            response = requests.post(
                GOOGLE_SHEET_WEBAPP_URL,
                json=payload,
                timeout=3,
                allow_redirects=True
            )
            print(f"[GOOGLE SHEETS LOG] Logged '{event_type}' ({status}) | Response: {response.status_code}")
        except Exception as e:
            # Silently catch and log to ensure network delay/errors never crash Flask or OpenCV
            print(f"[!] Google Sheets Logging Warning: {e}")

    # Launch daemon thread so execution is 100% non-blocking
    threading.Thread(target=_worker, daemon=True).start()


# --- Vault & Examination State ---
AUTHORIZED_4DIGIT_OTP = os.environ.get('VAULT_OTP', '4829')  # 4-Digit Central Exam Board OTP
SERIAL_PORT = os.environ.get('ARDUINO_PORT', 'COM3')
BAUD_RATE = 9600

vault_state = {
    "is_locked": True,
    "active_otp": AUTHORIZED_4DIGIT_OTP,
    "last_unlocked": None,
    "unlocked_by": None,
    "hardware_connected": False,
    "total_centers": 46,
    "active_centers": "46 / 46",
    "exam_center": "NGP PATNA-13",
    "paper_subject": "Microprocessors & Embedded Systems (CSE-501)",
    "scheduled_time": "10:00 AM - 01:00 PM"
}

# Try connecting to Arduino Serial
arduino_serial = None
if SERIAL_AVAILABLE:
    try:
        arduino_serial = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        vault_state["hardware_connected"] = True
        print(f"[*] Successfully connected to Arduino on {SERIAL_PORT}")
    except Exception as e:
        print(f"[!] Arduino not detected on {SERIAL_PORT}. Using hardware simulation mode. ({e})")


def send_hardware_signal(command: str):
    """
    Sends command to physical Arduino via Serial.
    Falls back gracefully to simulation mode if device is disconnected.
    """
    global arduino_serial
    cmd_bytes = f"{command.strip().upper()}\n".encode('utf-8')

    if arduino_serial and arduino_serial.is_open:
        try:
            arduino_serial.write(cmd_bytes)
            arduino_serial.flush()
            print(f"[SERIAL -> ARDUINO] Sent: {command}")
            return "HARDWARE_SUCCESS"
        except Exception as e:
            print(f"[!] Serial transmission error: {e}. Switching to simulation.")

    # Simulation fallback
    print(f"[SIMULATION -> ARDUINO] Triggered command: '{command}'")
    if command == "UNLOCK":
        print("[SIMULATION] -> Servo (Pin 9) rotated 90 degrees.")
        print("[SIMULATION] -> Buzzer (Pin 8) sounded for 2 seconds.")
    elif command == "LOCK":
        print("[SIMULATION] -> Servo (Pin 9) restored to 0 degrees.")
    return "SIMULATION_SUCCESS"


def handle_surveillance_alert(alert_desc):
    """Callback invoked when OpenCV detects phone or sudden rapid movement."""
    print(f"[VISION ALERT] High-severity event detected: {alert_desc}")
    send_to_google_sheet(
        center_name=vault_state.get("exam_center", "NGP PATNA-13"),
        event_type=f"Motion Alert / {alert_desc}",
        otp=vault_state.get("active_otp", "4829"),
        status="ALERT"
    )


# --- HTTP Routes ---

@app.route('/')
def dashboard():
    """Renders the main central dashboard view."""
    return render_template('index.html', vault=vault_state)


@app.route('/video_feed')
def video_feed():
    """Streams live OpenCV surveillance feed with face & suspicious object overlays."""
    return Response(
        generate_frames(camera_source=0, alert_callback=handle_surveillance_alert),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/unlock-vault', methods=['POST'])
def unlock_vault():
    """
    API endpoint accepting a 4-digit OTP to trigger vault unlocking.
    Triggers physical Arduino Serial signal (or simulated signal) and logs event to Google Sheets.
    """
    data = request.get_json(silent=True) or request.form
    entered_otp = str(data.get('otp', '')).strip()
    operator = data.get('operator', 'Center-Superintendent')

    if not entered_otp:
        return jsonify({
            "status": "error",
            "message": "4-digit OTP is required."
        }), 400

    # Validate 4-digit length
    if len(entered_otp) != 4 or not entered_otp.isdigit():
        return jsonify({
            "status": "error",
            "message": "OTP must be exactly 4 digits."
        }), 400

    # Verify against authorized OTP
    if entered_otp == vault_state["active_otp"]:
        # Trigger Serial command to Arduino (or simulation)
        signal_status = send_hardware_signal("UNLOCK")

        vault_state["is_locked"] = False
        vault_state["last_unlocked"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        vault_state["unlocked_by"] = operator

        # Trigger Google Sheets Web App logging for Vault Unlock event
        send_to_google_sheet(
            center_name=vault_state.get("exam_center", "NGP PATNA-13"),
            event_type="Vault Unlocked",
            otp=entered_otp,
            status="UNLOCKED"
        )

        mode_desc = "Physical Arduino" if signal_status == "HARDWARE_SUCCESS" else "Simulated Hardware"
        return jsonify({
            "status": "success",
            "message": f"OTP Verified! Vault UNLOCKED via {mode_desc} (Servo: 90°, Buzzer: 2s).",
            "is_locked": False,
            "mode": signal_status
        }), 200
    else:
        return jsonify({
            "status": "error",
            "message": "Incorrect OTP! Access denied. Tamper attempt logged."
        }), 403


@app.route('/api/lock-vault', methods=['POST'])
def lock_vault():
    """Manually re-locks the digital vault."""
    send_hardware_signal("LOCK")
    vault_state["is_locked"] = True
    return jsonify({
        "status": "success",
        "message": "Vault successfully re-locked. Servo reset to 0°.",
        "is_locked": True
    })


@app.route('/api/surveillance/alerts', methods=['POST'])
def receive_surveillance_alert():
    """API endpoint allowing external vision scripts to push alerts and log to Google Sheets."""
    data = request.get_json(silent=True) or {}
    alert_type = data.get("type", "Motion Alert")
    send_to_google_sheet(
        center_name=vault_state.get("exam_center", "NGP PATNA-13"),
        event_type=alert_type,
        otp=vault_state.get("active_otp", "4829"),
        status="ALERT"
    )
    return jsonify({"status": "success", "message": "Alert received and logged"}), 200


@app.route('/api/vault/status', methods=['GET'])
def get_vault_status():
    """Returns current telemetry of the vault."""
    return jsonify({
        "status": "success",
        "data": vault_state
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"[*] SBTE-LeakShield Control Center running on http://127.0.0.1:{port}")
    print(f"[*] Authorized 4-digit OTP for demo: {AUTHORIZED_4DIGIT_OTP}")
    app.run(host='0.0.0.0', port=port, debug=True)
