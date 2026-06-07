# Arduino Setup Guide — Grow Auto Control

## 1. Install the Arduino IDE

Download and install [Arduino IDE 2.x](https://www.arduino.cc/en/software) (Windows installer).

---

## 2. Install Required Libraries

Open the IDE → **Tools → Manage Libraries…** and install:

| Library | Author | Search term |
|---------|--------|-------------|
| DHT sensor library | Adafruit | `DHT` |
| Adafruit Unified Sensor | Adafruit | `Adafruit Unified Sensor` |

The Servo library ships with the IDE — no additional installation needed.

---

## 3. Select Board and Port

1. Connect the Arduino Mega 2560 via USB.
2. **Tools → Board → Arduino AVR Boards → Arduino Mega or Mega 2560**
3. **Tools → Processor → ATmega2560**
4. **Tools → Port** → select the COM port (e.g. COM4, CH340).

Close Serial Monitor and any Python app using the port before uploading.

---

## 4. Open and Upload the Sketch

1. **File → Open…** → `arduino/grow_control/grow_control.ino`
2. Click **Upload**.
3. Open **Tools → Serial Monitor**, baud **115 200**.
4. Confirm `GROW_CTRL_READY` and JSON lines every ~2 s.

---

## 5. Bench Wiring (Mega 2560)

### DHT11

```
DHT11           Mega 2560
------          ---------
VCC      →      3.3V
GND      →      GND
DATA     →      D4   (+ 10 kΩ pull-up to 3.3V if bare sensor)
```

### YL-69 soil moisture

```
YL-69           Mega 2560
-----           ---------
VCC      →      5V
GND      →      GND
AO       →      A1
DO       →      (not connected)
```

Calibrate `SOIL_ADC_WET` / `SOIL_ADC_DRY` in `.env` after installing the probe in substrate.

### Fan relay (JQC3F-05VDC-C, active LOW)

```
Relay module    Mega 2560
------------    ---------
VCC      →      5V
GND      →      GND
IN       →      D8          LOW = relay ON, HIGH = relay OFF
```

Relay power terminals (Chinese labels):

| Label | Meaning | Connect |
|-------|---------|---------|
| 公共 | COM | 9V (+) |
| 常开 | NO | Fan (+) |
| 常闭 | NC | (unused) |

```
9V (+) ── COM
NO ────── Fan (+)
Fan (−) ── 9V GND  (common with Arduino GND)
```

Bench uses a **9V battery** on a **12V-rated fan** (lower speed, acceptable for demo).

### Continuous-rotation servo (360°)

```
Servo           Mega 2560
-----           ---------
VCC (red)  →   5V
GND        →   GND
Signal     →   D9

90 = stop, 0 = spin CW (irrigation open in software)
```

Use a separate 5V supply for the servo if USB power is unstable (share GND with Mega).

### LED (future)

Reserved wire on **D7** + **220 Ω** resistor (not connected in current bench build).  
LED schedule runs in the **GUI only** (`LED_HARDWARE_ENABLED=false`).

---

## 6. `.env` (project root)

Copy `.env.example` → `.env`. Key values for this bench:

```ini
MOCK_HARDWARE=false
SERIAL_PORT=AUTODETECT
PIN_FAN_RELAY=8
RELAY_ACTIVE_LOW=true
PIN_SERVO=9
SERVO_STOP_ANGLE=90
SERVO_OPEN_ANGLE=0
LED_HARDWARE_ENABLED=false
PIN_LED_FUTURE=7
```

---

## 7. Run the Python Application

```powershell
poetry run python -m app
```

Status bar shows **Connected** when the handshake succeeds. Do not unplug USB during normal operation; if you do, the app reconnects and re-applies fan/servo logic automatically.
