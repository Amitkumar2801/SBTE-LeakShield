/*
 * SBTE-LeakShield: Hardware Digital Vault Controller
 * Microcontroller: Arduino Uno / Nano / Mega
 * 
 * Hardware Connections:
 * - Servo Motor Signal -> Pin 9
 * - Piezo Buzzer (+)   -> Pin 8
 * 
 * Description:
 * Listens for Serial commands from Python (Dashboard / Flask backend).
 * When it receives "UNLOCK":
 *   1. Rotates Servo motor (Pin 9) by 90 degrees to disengage the physical latch.
 *   2. Sounds Buzzer (Pin 8) for exactly 2 seconds.
 *   3. Reports confirmation status back over Serial.
 */

#include <Servo.h>

// --- Pin Assignments ---
const int SERVO_PIN  = 9;
const int BUZZER_PIN = 8;

// --- Servo Positions ---
const int POS_LOCKED   = 0;    // 0 degrees (Vault Locked)
const int POS_UNLOCKED = 90;   // 90 degrees (Vault Open)

Servo vaultServo;
bool isVaultLocked = true;

void setup() {
  // Initialize Serial communication at 9600 baud rate
  Serial.begin(9600);

  // Configure Buzzer pin
  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);

  // Attach and position Servo to initial locked state
  vaultServo.attach(SERVO_PIN);
  vaultServo.write(POS_LOCKED);
  isVaultLocked = true;

  Serial.println(F("[SYSTEM_READY] SBTE-LeakShield Hardware Vault Controller Initialized."));
  Serial.println(F("[WAITING] Listening for Serial commands ('UNLOCK', 'LOCK', 'STATUS')..."));
}

void loop() {
  // Check if command is received from Python via Serial
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    command.toUpperCase();

    if (command == "UNLOCK") {
      executeUnlockSequence();
    } else if (command == "LOCK") {
      executeLockSequence();
    } else if (command == "STATUS") {
      sendStatus();
    } else if (command.length() > 0) {
      Serial.print(F("[ERR] Unknown command: "));
      Serial.println(command);
    }
  }
}

/**
 * Executes the vault unlock sequence:
 * Rotates Servo by 90 degrees and sounds buzzer for 2 seconds.
 */
void executeUnlockSequence() {
  Serial.println(F("[ACTION] Valid 'UNLOCK' command received from Python."));

  // 1. Rotate Servo motor by 90 degrees
  vaultServo.write(POS_UNLOCKED);
  isVaultLocked = false;
  Serial.println(F("[SERVO] Rotated to 90 degrees (Latch Disengaged)."));

  // 2. Sound Buzzer for 2 seconds (2000 milliseconds)
  Serial.println(F("[BUZZER] Alert tone sounding for 2 seconds..."));
  tone(BUZZER_PIN, 1200);   // Sound 1.2 kHz alert tone
  digitalWrite(BUZZER_PIN, HIGH); // Also supports active buzzers
  delay(2000);              // Hold tone for 2 seconds
  noTone(BUZZER_PIN);       // Silence tone
  digitalWrite(BUZZER_PIN, LOW);

  // 3. Send final status response back to Python
  Serial.println(F("[SUCCESS] Vault is now UNLOCKED."));
}

/**
 * Re-engages the mechanical servo lock back to 0 degrees.
 */
void executeLockSequence() {
  vaultServo.write(POS_LOCKED);
  isVaultLocked = true;

  // Short 100ms confirmation chirp
  tone(BUZZER_PIN, 800, 100);
  Serial.println(F("[SUCCESS] Vault is now LOCKED."));
}

/**
 * Returns JSON status over Serial for telemetry.
 */
void sendStatus() {
  Serial.print(F("{\"vault_locked\": "));
  Serial.print(isVaultLocked ? F("true") : F("false"));
  Serial.println(F("}"));
}
