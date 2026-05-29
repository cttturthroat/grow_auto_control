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
4. **Tools → Port** → select the COM port that appeared after plugging in the board
   (check Device Manager if unsure — it lists as "USB Serial Device (COMx)").

---

## 4. Open and Upload the Sketch

1. **File → Open…** → navigate to `arduino/grow_control/grow_control.ino`
2. Click the **Upload** button (→ arrow).
3. Wait for "Done uploading."
4. Open **Tools → Serial Monitor**, set baud rate to **115 200**.
   You should see `GROW_CTRL_READY` within 2–3 seconds, followed by JSON lines.

---

## 5. Wiring Diagram

All voltages are 5 V from the Arduino unless otherwise noted.

### DHT11 (already connected)

```
DHT11           Mega 2560
------          ---------
VCC      →      5V
GND      →      GND
DATA     →      D4   (+ 10 kΩ pull-up resistor between DATA and 5V)
```

### YL-69 Soil Moisture Sensor

```
YL-69           Mega 2560
-----           ---------
VCC      →      5V
GND      →      GND
AO       →      A1   (analog out — lower = wetter)
DO       →      (leave unconnected)
```

> **Calibration** — after wiring, measure `soilRaw` in your JSON output:
> - Dip the probe in water → note the value → set `SOIL_ADC_WET` in `.env`
> - Hold the probe in dry air → note the value → set `SOIL_ADC_DRY` in `.env`

### Fan + Relay Module (5 V trigger, active HIGH)

```
Relay module    Mega 2560
------------    ---------
VCC      →      5V
GND      →      GND
IN       →      D7
```

Connect the fan between the relay's **NO** (Normally Open) and **COM** terminals.
Power the fan from an appropriate external supply (12 V / 5 V depending on your fan).

### Micro Servo

```
Servo           Mega 2560
-----           ---------
VCC (red)  →   5V
GND (black) →  GND
Signal (orange/white) → D9
```

> Note: if you drive multiple servos or a large servo, use an external 5 V supply
> for VCC and connect only GND and signal to the Mega.

### RGB LED (common cathode)

Each colour pin goes through a **220 Ω resistor**.

```
LED pin         Resistor        Mega 2560
-------         --------        ---------
R anode    →   220 Ω      →    D2
G anode    →   220 Ω      →    D3
B anode    →   220 Ω      →    D5
Common (-)  ←──────────────────GND
```

**Common anode LED**: wire the common (+) pin to 5V; colour pins to resistors then
to D2/D3/D5 as above. Set `LED_COMMON_ANODE=true` in `.env`.

> **Why pins 2, 3, 5?**
> The Servo library on Mega uses Timer 1 internally, disabling `analogWrite` on
> pins 11 and 12. Pins 2, 3, 5 use Timer 3 — unaffected by the Servo library.

---

## 6. Environment variables (`.env`)

Copy `.env.example` to `.env` in the project root and verify these values match
your wiring:

```ini
MOCK_HARDWARE=false
SERIAL_PORT=AUTODETECT    # or e.g. COM5
SERIAL_BAUD=115200
PIN_DHT=4
PIN_SOIL_ANALOG=1
PIN_FAN_RELAY=7
PIN_SERVO=9
PIN_LED_R=2
PIN_LED_G=3
PIN_LED_B=5
LED_COMMON_ANODE=false
SOIL_ADC_WET=300          # update after calibration
SOIL_ADC_DRY=900          # update after calibration
```

---

## 7. Run the Python Application

```powershell
poetry run python -m app
```

The app connects automatically (serial port auto-detected by USB device descriptor).
The status bar shows **Connected** within a few seconds of launch.
