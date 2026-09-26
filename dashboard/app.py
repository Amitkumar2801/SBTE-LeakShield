import cv2
import threading
import requests
import serial
import time
from flask import Flask, render_template, Response, request, jsonify

app = Flask(__name__)

# ==========================================
# CONFIGURATION
# ==========================================
GOOGLE_SHEET_WEBAPP_URL = "https://script.google.com/macros/s/AKfycbw-E5qG1l_ChhXKTG1lxYV8O0xHUNAW4iXOP8yWBQqNsmBMJugcH2d6ET8RlX56fL1c/exec"
CENTER_NAME = "NGP PATNA-13"
CURRENT_OTP = "4829"
COM_PORT = "COM3"  # Change to your actual Arduino COM port (e.g. COM3, COM4)
BAUD_RATE = 9600

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
            requests.post(GOOGLE_SHEET_WEBAPP_URL, json=payload, timeout=3)
            print(f"Successfully logged event to Google Sheet: {event_type}")
        except Exception as err:
            print(f"Google Sheet logging error: {err}")

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

# ==========================================
# OPENCV CAMERA & AI SURVEILLANCE
# ==========================================
def generate_frames():
    camera = cv2.VideoCapture(0)
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    
    prev_gray = None
    last_alert_time = 0

    while True:
        success, frame = camera.read()
        if not success:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

        # Face Detection Bounding Box
        for (x, y, w, h) in faces:
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            cv2.putText(frame, "HUMAN PRESENT", (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        # Rapid Motion & Activity Detection
        suspicious_detected = False
        if prev_gray is not None:
            frame_diff = cv2.absdiff(prev_gray, gray)
            _, thresh = cv2.threshold(frame_diff, 25, 255, cv2.THRESH_BINARY)
            non_zero_count = cv2.countNonZero(thresh)

            if non_zero_count > 15000:  # Threshold for rapid movement / phone interaction
                suspicious_detected = True
                cv2.putText(frame, "SUSPICIOUS ACTIVITY: RAPID MOVEMENT", (20, 40), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                
                # Rate-limited Google Sheet alert logging (every 10 seconds)
                current_time = time.time()
                if current_time - last_alert_time > 10:
                    send_to_google_sheet_async("Suspicious Motion / Phone Alert", "N/A", "ALERT")
                    last_alert_time = current_time

        prev_gray = gray

        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

# ==========================================
# FLASK ROUTES
# ==========================================
@app.route('/')
def index():
    vault_status = {
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
    return render_template('index.html', otp=CURRENT_OTP, center=CENTER_NAME, vault=vault_status)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/verify_otp', methods=['POST'])
@app.route('/api/unlock-vault', methods=['POST'])
def verify_otp():
    global vault_unlocked
    data = request.get_json(silent=True) or request.form
    entered_otp = str(data.get('otp', '')).strip()

    if entered_otp == CURRENT_OTP:
        vault_unlocked = True
        send_hardware_command('U')  # 'U' for Unlock (Servo 90 deg + Buzzer tone)
        send_to_google_sheet_async("OTP Verified - Vault Unlocked", entered_otp, "UNLOCKED")
        return jsonify({"status": "success", "message": "Vault Unlocked Successfully!", "is_locked": False})
    else:
        return jsonify({"status": "error", "message": "Invalid OTP!"}), 400

@app.route('/lock_vault', methods=['POST'])
@app.route('/api/lock-vault', methods=['POST'])
def lock_vault():
    global vault_unlocked
    vault_unlocked = False
    send_hardware_command('L')  # 'L' for Lock (Servo 0 deg)
    send_to_google_sheet_async("Vault Locked Manually", CURRENT_OTP, "LOCKED")
    return jsonify({"status": "success", "message": "Vault Locked Successfully!", "is_locked": True})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)