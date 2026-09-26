#include <Servo.h>

Servo vaultServo;

const int SERVO_PIN = 9;
const int BUZZER_PIN = 8;

void setup() {
  Serial.begin(9600); // Serial port for Python communication
  vaultServo.attach(SERVO_PIN);
  vaultServo.write(0); // Default: Vault Locked (0 degrees)

  pinMode(BUZZER_PIN, OUTPUT);
  digitalWrite(BUZZER_PIN, LOW);
}

void loop() {
  if (Serial.available() > 0) {
    char command = Serial.read();

    if (command == 'U') {
      // Command 'U' -> UNLOCK VAULT
      vaultServo.write(90); // Rotate servo to 90 degrees

      // Buzzer Alert Tone (2 seconds)
      digitalWrite(BUZZER_PIN, HIGH);
      delay(2000);
      digitalWrite(BUZZER_PIN, LOW);
    } else if (command == 'L') {
      // Command 'L' -> LOCK VAULT
      vaultServo.write(0); // Reset servo to 0 degrees
      digitalWrite(BUZZER_PIN, LOW);
    }
  }
}