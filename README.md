# 🛡️ SBTE-LeakShield

> **AI-Powered Digital Vault & Real-Time Exam Hall Surveillance System**  
> *A scalable, zero-trust examination security solution designed for all 46 Government Polytechnics in Bihar under SBTE.*

---

## 📌 Problem Statement

Ensuring **leak-proof question paper distribution** and **malpractice-free exam halls** across 46 technical institutes in Bihar is a major security challenge. 

* **Paper Leak Vulnerability:** Physical locks and traditional transit carry high risks of unauthorized tampering.
* **Exam Hall Malpractices:** Manual invigilation often struggles to detect hidden mobile phones, impersonation, or concealed identities in real time.

---

## ⚡ The Solution: SBTE-LeakShield

**SBTE-LeakShield** delivers an integrated, two-tier defense system:

1. **🔐 Smart Digital Vault (IoT):** A tamper-proof physical question paper trunk that unlocks **ONLY** when a synchronized, time-triggered 4-digit OTP/signal is issued from the central SBTE Web Board.
2. **👁️ Smart Hall Surveillance (Vision AI):** An automated computer vision engine that continuously monitors exam hall cameras to detect unauthorized devices (phones), suspicious postures, and sudden rapid motion.

---

## 🏗️ System Architecture & Workflow

```text
               ┌──────────────────────────────────────┐
               │    SBTE Central Board Dashboard      │
               └──────────────────┬───────────────────┘
                                  │
                       (Encrypted OTP / Signal)
                                  │
                                  ▼
               ┌──────────────────────────────────────┐
               │        Flask Web Backend             │
               └──────────┬────────────────┬──────────┘
                          │                │
            ┌─────────────┴──┐          ┌──┴───────────────┐
            │ Hardware Vault │          │  Vision AI Engine│
            │ (Servo Lock)   │          │ (OpenCV Feed)    │
            └─────────────┬──┘          └──┬───────────────┘
                          │                │
                          ▼                ▼
                     Vault Unlocks    Real-Time Alert 🚨
```

---

## 👥 Team: SBTE-LeakShield

* **Developer / Coder Lead:** AMIT KUMAR
* **Hardware & Circuit Lead:** JITENDRA KUMAR
* **Research & Pitch Lead:** Badal kumar
* **Demo & Operations Lead:** Kishan raj

---

## 📂 Project Structure

```text
SBTE-LeakShield/
├── dashboard/
│   ├── app.py                  # Main Flask application backend (OTP verification, video stream)
│   ├── static/                 # CSS styles & UI assets
│   │   └── style.css           # Modern cyber-security dark UI
│   └── templates/              # HTML Web Views (Dashboard & Vault Control)
│       └── index.html          # Interactive dashboard for 46 exam centers
├── ai_surveillance/
│   ├── detect.py               # Real-time OpenCV face, phone & rapid motion detection
│   └── models/                 # Cascade classifiers / detection weights
│       └── README.md
├── hardware/
│   └── vault_control.ino       # Microcontroller C++ code for Servo & Buzzer
└── README.md                   # Project Documentation
```

---

## 🚀 Quickstart Guide

### 1. Launch Central Dashboard (Flask Web Backend)
```bash
# Navigate to the dashboard directory
cd dashboard

# Install requirements
pip install flask requests pyserial opencv-python

# Run the server
python app.py
```
Open [http://localhost:5000](http://localhost:5000) to access the central dashboard.

### 2. Run Real-Time AI Surveillance
```bash
# Navigate to surveillance module
cd ai_surveillance

# Install OpenCV dependencies
pip install opencv-python numpy requests

# Run detection engine
python detect.py --source 0
```

### 3. Hardware Vault Microcontroller Setup
1. Open [`hardware/vault_control.ino`](file:///c:/SBTE-LeakShield/hardware/vault_control.ino) in Arduino IDE.
2. Select your board (Arduino Uno / Nano / ESP32) and COM port.
3. Wire the servo motor to Pin 9 and buzzer to Pin 8.
4. Upload firmware to the microcontroller.
