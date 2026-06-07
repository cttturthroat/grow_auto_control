/*
 * grow_control.ino — Automated Microgreens Farming Controller
 * Target board: Arduino Mega 2560
 *
 * REQUIRED LIBRARIES  (Arduino IDE → Tools → Manage Libraries…)
 *   • "DHT sensor library"    by Adafruit
 *   • "Adafruit Unified Sensor" by Adafruit
 *
 * WIRING  (bench — must match app/core/config.py and .env)
 *
 *  DHT11 VCC              3.3V
 *  DHT11 DATA             D4
 *  DHT11 GND              GND
 *
 *  YL-69 VCC              5V
 *  YL-69 GND              GND
 *  YL-69 AO               A1
 *
 *  Relay VCC              5V
 *  Relay GND              GND
 *  Relay IN               D8          Active LOW (JQC3F): LOW = ON, HIGH = OFF
 *
 *  Fan 9V (+)             Relay COM
 *  Fan 9V (+) return      Relay NO
 *  Fan (−)                9V GND (common with Arduino GND)
 *
 *  Continuous servo VCC   5V
 *  Continuous servo GND   GND
 *  Continuous servo SIG   D9          90 = stop, 0 = spin CW (irrigation)
 *
 *  D7                     reserved (future single LED + 220 Ω)
 *
 * SERIAL PROTOCOL  (115 200 baud, newline-terminated)
 *  Board → Host:  GROW_CTRL_READY
 *                 {"s":450,"t":24.5,"h":63.0}
 *  Host → Board:  DOUT <pin> <0|1>
 *                 SERVO <pin> <0-180>
 *                 PWM <pin> <0-255>
 */

#include <DHT.h>
#include <Servo.h>

#define DHT_PIN        4
#define SOIL_PIN       A1
#define FAN_RELAY_PIN  8
#define SERVO_PIN      9

#define SERVO_STOP     90
#define RELAY_OFF      HIGH
#define RELAY_ON       LOW

#define DHT_TYPE       DHT11
#define READ_INTERVAL  2000UL
#define BAUD_RATE      115200
#define CMD_BUF_SIZE   64

DHT          dht(DHT_PIN, DHT_TYPE);
Servo        growServo;
char         cmdBuf[CMD_BUF_SIZE];
uint8_t      cmdLen    = 0;
unsigned long lastReadMs = 0;

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(FAN_RELAY_PIN, OUTPUT);
  digitalWrite(FAN_RELAY_PIN, RELAY_OFF);

  dht.begin();

  growServo.attach(SERVO_PIN);
  growServo.write(SERVO_STOP);

  delay(2000);
  Serial.println("GROW_CTRL_READY");
}

void loop() {
  processSerial();

  unsigned long now = millis();
  if (now - lastReadMs >= READ_INTERVAL) {
    lastReadMs = now;
    sendReading();
  }
}

void processSerial() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n') {
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

void handleCommand(const char* cmd) {
  if (strncmp(cmd, "DOUT ", 5) == 0) {
    int pin, val;
    if (sscanf(cmd + 5, "%d %d", &pin, &val) == 2) {
      pinMode(pin, OUTPUT);
      digitalWrite(pin, val ? HIGH : LOW);
    }
  } else if (strncmp(cmd, "SERVO ", 6) == 0) {
    int pin, angle;
    if (sscanf(cmd + 6, "%d %d", &pin, &angle) == 2) {
      (void)pin;
      growServo.write(constrain(angle, 0, 180));
    }
  } else if (strncmp(cmd, "PWM ", 4) == 0) {
    int pin, duty;
    if (sscanf(cmd + 4, "%d %d", &pin, &duty) == 2) {
      pinMode(pin, OUTPUT);
      analogWrite(pin, constrain(duty, 0, 255));
    }
  }
}

void sendReading() {
  int   soilRaw = analogRead(SOIL_PIN);
  float temp    = dht.readTemperature();
  float hum     = dht.readHumidity();

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
