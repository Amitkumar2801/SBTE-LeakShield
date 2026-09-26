# 🛡️ SBTE-LeakShield

> **AI-Powered Digital Vault & Real-Time Exam Hall Surveillance System**  
> *A scalable, zero-trust examination security solution designed for all Government Polytechnics in Bihar under SBTE.*

---

## 📌 Problem Statement

Ensuring **leak-proof question paper distribution** and **malpractice-free exam halls** across technical institutes in Bihar is a major security challenge. 

* **Paper Leak Vulnerability:** Physical locks and traditional transit carry high risks of unauthorized tampering.
* **Exam Hall Malpractices:** Manual invigilation often struggles to detect hidden mobile phones, impersonation, or concealed identities in real time.

---

## ⚡ The Solution: SBTE-LeakShield

**SBTE-LeakShield** delivers an integrated, two-tier defense system:

1. **🔐 Smart Digital Vault (IoT):** A tamper-proof physical question paper trunk that unlocks **ONLY** when a synchronized, time-triggered OTP/signal is issued from the central SBTE Web Board.
2. **👁️ Smart Hall Surveillance (Vision AI):** An automated computer vision engine that continuously monitors exam hall cameras to detect unauthorized devices (phones), suspicious postures, and identity concealment.

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
