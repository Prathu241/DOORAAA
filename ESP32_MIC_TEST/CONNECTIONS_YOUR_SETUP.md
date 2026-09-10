# EXACT CONNECTIONS FOR YOUR SETUP

## Your Hardware
- **ESP32-S3 DevKit** (on breadboard)
- **INMP441 Microphone Module** (circular with 6 pins)
- **Breadboard** (solderless)
- **Jumper Wires** (male-to-male)
- **USB TTL** (optional, for serial debug)

---

## INMP441 PIN IDENTIFICATION

Looking at your circular INMP441 module (flat side shows pin labels):

```
        [FLAT SIDE - Pin Labels Visible]
        
    GND ---- VCC
    L/R ---- WS
    SCK ---- SD
    
Pinout from top-left clockwise:
1. GND   (Ground)
2. L/R   (Mono select - must connect to GND)
3. SCK   (Bit Clock)
4. SD    (Serial Data/DIN)
5. WS    (Word Select/LRCK)
6. VCC   (3.3V Power)
```

---

## BREADBOARD CONNECTION DIAGRAM

```
Breadboard (Your layout):
┌─────────────────────────────────────────┐
│  TOP RAIL (Power)                       │
│  [+] [+] [+] [+] [+] | [+] [+] [+] [+] │
│  [ ] [ ] [ ] [ ] [ ] | [ ] [ ] [ ] [ ] │
│  [-] [-] [-] [-] [-] | [-] [-] [-] [-] │
│  [−] [−] [−] [−] [−] | [−] [−] [−] [−] │
│  BOTTOM RAIL (Ground)                   │
└─────────────────────────────────────────┘

Your ESP32-S3 sits on RIGHT SIDE of breadboard
INMP441 module sits on LEFT SIDE
```

---

## STEP-BY-STEP WIRING

### POWER CONNECTIONS (Do First - Verify No Shorts!)

#### 1. 3.3V Power Rail
```
ESP32-S3 3.3V pin 
    ↓
Top RIGHT [+] rail (Positive)
    ↓
Connect RED jumper wire to 
INMP441 VCC (Pin 6 - usually marked VCC)
```

**Action:**
- Locate ESP32-S3 **3.3V** pin (top side, left connector area)
- Plug RED wire into 3.3V pin
- Route wire to **top-left [+] rail** (power rail) on breadboard
- Plug INMP441 VCC (pin 6) into the same power rail

#### 2. Ground Connections (2 wires needed)
```
ESP32-S3 GND pin 
    ↓
Bottom RIGHT [-] rail (Ground)
    ↓
Connect:
  - BLACK wire to INMP441 GND (Pin 1)
  - BLACK wire to INMP441 L/R (Pin 2) ← BOTH to GND!

This sets INMP441 to MONO mode (left channel only)
```

**Action:**
- Locate ESP32-S3 **GND** pin (multiple available - use any)
- Plug BLACK wire into ESP32 GND
- Route to **bottom-left [-] rail** (ground rail)
- From ground rail, run two separate BLACK wires:
  - One to INMP441 **GND (Pin 1)**
  - One to INMP441 **L/R (Pin 2)**

**Verify before proceeding:**
- [x] No RED wire touches BLACK wire
- [x] 3.3V rail not shorted to GND rail
- [x] All connections solid (not loose)

---

### I2S SIGNAL CONNECTIONS (GPIO Pins)

After power is verified safe, add these 3 signal wires:

#### 3. Clock Signal: GPIO 4 → INMP441 SCK

```
ESP32-S3 GPIO 4 
    ↓ [YELLOW wire]
BREADBOARD middle area
    ↓
INMP441 SCK (Pin 3)
```

**Action:**
- Find **GPIO 4** on ESP32-S3 left side (labeled "4")
- Plug YELLOW wire into GPIO 4
- Route to INMP441 **SCK (Pin 3)**
- Plug in firmly

#### 4. Word Select: GPIO 5 → INMP441 WS

```
ESP32-S3 GPIO 5 
    ↓ [GREEN wire]
BREADBOARD middle area
    ↓
INMP441 WS (Pin 5)
```

**Action:**
- Find **GPIO 5** on ESP32-S3 left side (labeled "5")
- Plug GREEN wire into GPIO 5
- Route to INMP441 **WS (Pin 5)**
- Plug in firmly

#### 5. Data Input: GPIO 6 → INMP441 SD

```
ESP32-S3 GPIO 6 
    ↓ [BLUE wire]
BREADBOARD middle area
    ↓
INMP441 SD (Pin 4)
```

**Action:**
- Find **GPIO 6** on ESP32-S3 left side (labeled "6")
- Plug BLUE wire into GPIO 6
- Route to INMP441 **SD (Pin 4)**
- Plug in firmly

---

## FINAL CONNECTION CHECKLIST

- [x] **RED wire:** 3.3V → INMP441 VCC (Pin 6)
- [x] **BLACK wire:** GND → INMP441 GND (Pin 1)
- [x] **BLACK wire:** GND → INMP441 L/R (Pin 2) ← Mono mode
- [x] **YELLOW wire:** GPIO 4 → INMP441 SCK (Pin 3)
- [x] **GREEN wire:** GPIO 5 → INMP441 WS (Pin 5)
- [x] **BLUE wire:** GPIO 6 → INMP441 SD (Pin 4)

**Total: 6 wires (3.3V, 2× GND, SCK, WS, SD)**

---

## USB TTL CONNECTION (Optional - For Serial Debug)

If you want serial output **without** USB:

```
ESP32-S3 UART0    USB TTL Module
─────────────────  ────────────
TX0 (GPIO 43)  →   RXD (white)
RX0 (GPIO 44)  ←   TXD (green)
GND            →   GND (black)
```

Then connect USB TTL to your PC for serial monitor at **9600 baud**.

**BUT:** Easiest is just use ESP32 USB cable directly.

---

## PHOTO REFERENCE

Your INMP441 shows:
```
    GND (1)  VCC (6)
    L/R (2)  WS  (5)
    SCK (3)  SD  (4)
```

Match these exactly to connections above.

---

## NEXT: FLASH THE FIRMWARE

Once wired:

1. **Open Arduino IDE**
2. **Copy `mic_test.ino` code** into new sketch
3. **Select Board:** Tools → Board → ESP32-S3 Dev Module
4. **Select Port:** Tools → Port → COM? (your ESP32's USB port)
5. **Click Upload** (Ctrl+U)
6. **Wait for:** `Leaving... Hard resetting via RTS pin`
7. **Open Serial Monitor** (Tools → Serial Monitor, 9600 baud)
8. **See output:**
   ```
   =====================================================
   DORA MICROPHONE TEST
   ...
   ```

---

## VERIFICATION AFTER FLASHING

- **Speak into microphone**
- **Watch RMS and peak values jump up** in serial monitor
- **When silent:** Values drop back to near 0
- **If working:** Report "**MIC PASS**"
- **If not working:** Report error message

---

**Ready? Start wiring! Then let me show you training terminal.**
