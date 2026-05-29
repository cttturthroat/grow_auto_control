/*
 * grow_control.ino — Automated Microgreens Farming Controller
 * Target board: Arduino Mega 2560
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * REQUIRED LIBRARIES  (Arduino IDE → Tools → Manage Libraries…)
 * ═══════════════════════════════════════════════════════════════════════════
 *   • "DHT sensor library"    by Adafruit   (search: DHT)
 *   • "Adafruit Unified Sensor" by Adafruit (dependency of the above)
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * WIRING  (Arduino Mega 2560)
 * ═══════════════════════════════════════════════════════════════════════════
 *
 *  Component              Board pin   Notes
 *  ─────────────────────────────────────────────────────────────────────────
 *  DHT11 VCC              5V
 *  DHT11 DATA             D4          + 10 kΩ pull-up resistor to 5V
 *  DHT11 GND              GND
 *
 *  YL-69 VCC              5V
 *  YL-69 GND              GND
 *  YL-69 AO               A1          Analog output (lower = wetter)
 *  YL-69 DO               (unused)
 *
 *  Relay module VCC       5V
 *  Relay module GND       GND
 *  Relay module IN        D7          HIGH → relay closes → fan on
 *
 *  Micro servo VCC        5V
 *  Micro servo GND        GND
 *  Micro servo signal     D9
 *
 *  RGB LED (common cathode):
 *    Common cathode (+)   5V          (anode side; note: wired to 5V here)
 *    R anode              D2          220 Ω resistor in series
 *    G anode              D3          220 Ω resistor in series
 *    B anode              D5          220 Ω resistor in series
 *
 *  RGB LED (common anode): same wiring, set LED_COMMON_ANODE=true in .env
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * WHY PINS 2 / 3 / 5 FOR THE LED?
 * ═══════════════════════════════════════════════════════════════════════════
 *  On Arduino Mega 2560 the Servo library uses Timer 1, which disables
 *  analogWrite on pins 11 and 12 (OC1A / OC1B).  Pins 2, 3, 5 are driven
 *  by Timer 3 and remain fully functional alongside the servo.
 *
 * ═══════════════════════════════════════════════════════════════════════════
 * SERIAL PROTOCOL  (115 200 baud, newline-terminated)
 * ═══════════════════════════════════════════════════════════════════════════
 *  Board → Host (on boot):  GROW_CTRL_READY
 *  Board → Host (2 s tick): {"s":450,"t":24.5,"h":63.0}
 *    s = raw soil ADC (0–1023)
 *    t = temperature °C   (absent when DHT11 read fails)
 *    h = air humidity %   (absent when DHT11 read fails)
 *
 *  Host → Board:  DOUT <pin> <0|1>      digital write
 *                 SERVO <pin> <0-180>   servo angle
 *                 PWM <pin> <0-255>     PWM duty cycle
 */

#include <DHT.h>
#include <Servo.h>

// ─── Pin map (must match app/core/config.py) ────────────────────────────────
#define DHT_PIN        4
#define SOIL_PIN       A1
#define FAN_RELAY_PIN  7
#define SERVO_PIN      9
#define LED_R_PIN      2
#define LED_G_PIN      3
#define LED_B_PIN      5

// ─── Constants ───────────────────────────────────────────────────────────────
#define DHT_TYPE       DHT11
#define READ_INTERVAL  2000UL   // ms — DHT11 needs ≥ 1 s between reads
#define BAUD_RATE      115200
#define CMD_BUF_SIZE   64

// ─── Globals ─────────────────────────────────────────────────────────────────
DHT          dht(DHT_PIN, DHT_TYPE);
Servo        growServo;
char         cmdBuf[CMD_BUF_SIZE];
uint8_t      cmdLen    = 0;
unsigned long lastReadMs = 0;

// ════════════════════════════════════════════════════════════════════════════
void setup() {
  Serial.begin(BAUD_RATE);

  dht.begin();

  growServo.attach(SERVO_PIN);
  growServo.write(0);  // start closed

  pinMode(FAN_RELAY_PIN, OUTPUT);
  digitalWrite(FAN_RELAY_PIN, LOW);

  // LED off at startup
  analogWrite(LED_R_PIN, 0);
  analogWrite(LED_G_PIN, 0);
  analogWrite(LED_B_PIN, 0);

  // Opening the USB serial port resets the Arduino.
  // Wait for power-rails to stabilise, then announce readiness.
  delay(2000);
  Serial.println("GROW_CTRL_READY");
}

// ════════════════════════════════════════════════════════════════════════════
void loop() {
  processSerial();

  unsigned long now = millis();
  if (now - lastReadMs >= READ_INTERVAL) {
    lastReadMs = now;
    sendReading();
  }
}

// ─── Non-blocking serial reader ─────────────────────────────────────────────
void processSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
      // Trim trailing CR if any
      while (cmdLen > 0 && cmdBuf[cmdLen - 1] == '\r') {
        cmdLen--;
      }
      cmdBuf[cmdLen] = '\0';
      if (cmdLen > 0) {
        handleCommand(cmdBuf);
      }
      cmdLen = 0;
    } else if (cmdLen < CMD_BUF_SIZE - 1) {
      cmdBuf[cmdLen++] = c;
    }
  }
}

// ─── Command dispatcher ──────────────────────────────────────────────────────
void handleCommand(const char* cmd) {
  // DOUT <pin> <0|1>
  if (strncmp(cmd, "DOUT ", 5) == 0) {
    int pin, val;
    if (sscanf(cmd + 5, "%d %d", &pin, &val) == 2) {
      pinMode(pin, OUTPUT);
      digitalWrite(pin, val ? HIGH : LOW);
    }

  // SERVO <pin> <angle>
  } else if (strncmp(cmd, "SERVO ", 6) == 0) {
    int pin, angle;
    if (sscanf(cmd + 6, "%d %d", &pin, &angle) == 2) {
      growServo.write(constrain(angle, 0, 180));
    }

  // PWM <pin> <duty>
  } else if (strncmp(cmd, "PWM ", 4) == 0) {
    int pin, duty;
    if (sscanf(cmd + 4, "%d %d", &pin, &duty) == 2) {
      analogWrite(pin, constrain(duty, 0, 255));
    }
  }
}

// ─── Sensor reading + JSON output ────────────────────────────────────────────
void sendReading() {
  int   soilRaw = analogRead(SOIL_PIN);
  float temp    = dht.readTemperature();
  float hum     = dht.readHumidity();

  // Soil is always included; temperature/humidity only when DHT11 succeeds.
  Serial.print("{\"s\":");
  Serial.print(soilRaw);

  if (!isnan(temp) && !isnan(hum)) {
    Serial.print(",\"t\":");
    Serial.print(temp, 1);
    Serial.print(",\"h\":");
    Serial.print(hum, 1);
  }

  Serial.println("}");
}
