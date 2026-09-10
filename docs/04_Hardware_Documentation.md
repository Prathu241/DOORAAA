# Hardware Documentation
## Document 04 — SIH26172 | DORA

---

## 1. Bill of Materials

**Total BOM cost: < ₹800**

| # | Component | Part Number / Model | Qty | Approx. Cost |
|---|---|---|---|---|
| 1 | Microcontroller | ESP32-S3-DevKitC-1 N8R8 (8 MB flash, 8 MB PSRAM) | 1 | ₹600 |
| 2 | Microphone | INMP441 I2S MEMS module | 1 | ₹80 |
| 3 | Power (dev) | USB-C cable | 1 | — |
| 4 | Power (portable) | LiPo 3.7V 1000 mAh + TP4056 charging module | 1 | ₹100 |
| 5 | Wiring | Jumper wires (male-female) | 6 | ₹20 |
| **Total** | | | | **< ₹800** |

---

## 2. Microcontroller Specifications

### ESP32-S3-DevKitC-1 N8R8

| Parameter | Value |
|---|---|
| CPU | Dual-core Xtensa LX7, up to 240 MHz |
| Internal SRAM | 512 KB |
| PSRAM (external) | 8 MB (OPI PSRAM via SPI) |
| Flash | 8 MB (Quad SPI NOR) |
| Wi-Fi | 802.11 b/g/n 2.4 GHz |
| Bluetooth | BLE 5.0 |
| I2S Peripherals | 2× (I2S0 used for INMP441) |
| USB | Native USB-OTG (for firmware flash + monitor) |
| Operating Voltage | 3.3 V |
| Current (active, Wi-Fi on) | ~240 mA |
| Current (modem sleep) | ~20 mA |

> **Why N8R8?** The 8 MB PSRAM is critical. Without it, the tensor arena, ring buffer, and Opus encoder state would overflow the 512 KB internal SRAM. With PSRAM, only latency-critical buffers need to live in internal RAM.

---

## 3. Microphone Specifications

### INMP441 I2S MEMS Microphone

| Parameter | Value |
|---|---|
| Interface | I2S (PDM not supported) |
| Sample Rate | Up to 51.6 kHz (used at 16 kHz) |
| Bit Depth | 24-bit (ESP-IDF driver reads 16-bit) |
| SNR | 61 dB |
| Sensitivity | −26 dBFS |
| Frequency Response | 60 Hz – 15 kHz |
| Operating Voltage | 1.8 V – 3.3 V |
| Current | ~1.4 mA |
| Channel Select | L/R pin — GND = LEFT channel |

---

## 4. I2S Wiring — INMP441 → ESP32-S3

```
INMP441 Pin    ESP32-S3 GPIO     Function
─────────────────────────────────────────────
VDD        ──▶  3.3 V            Power
GND        ──▶  GND              Ground
WS         ──▶  GPIO 4           LRCLK / Word Select
SCK        ──▶  GPIO 5           BCLK / Bit Clock
SD         ──▶  GPIO 6           Serial Data (mic → MCU)
L/R        ──▶  GND              Channel select: LEFT
```

### Wiring Diagram (ASCII)

```
  ESP32-S3-DevKitC-1
  ┌────────────────┐
  │            3V3 │──────────────── VDD  ┐
  │            GND │──────────────── GND  │
  │          GPIO4 │──────────────── WS   │  INMP441
  │          GPIO5 │──────────────── SCK  │  I2S MEMS
  │          GPIO6 │──────────────── SD   │
  │                │            GND ── L/R┘
  └────────────────┘
```

> **Note:** L/R pin tied to GND selects the LEFT channel. If using two INMP441s for stereo, tie one to GND (LEFT) and one to VDD (RIGHT).

---

## 5. ESP-IDF I2S Driver Configuration

The firmware configures I2S using the ESP-IDF v5.2+ new-style driver:

```c
i2s_std_config_t std_cfg = {
    .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(16000),     // 16 kHz sample rate
    .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
                    I2S_DATA_BIT_WIDTH_16BIT,
                    I2S_SLOT_MODE_MONO),                // Mono, 16-bit
    .gpio_cfg = {
        .mclk = I2S_GPIO_UNUSED,
        .bclk = GPIO_NUM_5,                            // SCK
        .ws   = GPIO_NUM_4,                            // WS
        .dout = I2S_GPIO_UNUSED,
        .din  = GPIO_NUM_6                             // SD
    },
};
```

- **DMA buffer:** 512 samples per buffer = 32 ms of audio per DMA interrupt
- **DMA buffer count:** 4 (default) — provides ~128 ms of DMA headroom

---

## 6. Power Options

### Option A: USB-C (Development)

Connect the ESP32-S3-DevKitC-1 directly to a laptop or USB power bank via USB-C. Current draw during active Wi-Fi + I2S: ~240 mA. Any USB port provides sufficient power.

### Option B: LiPo Battery (Portable Demo / Field)

```
LiPo 3.7V 1000 mAh
        │
        ▼
  TP4056 module
   ├── OUT+ → ESP32 5V pin (via onboard 3.3V LDO)
   └── OUT- → GND
```

Runtime estimate at 240 mA continuous: ~4 hours. For demonstration (keyword detection every few minutes, modem sleep otherwise): ~12–24 hours.

---

## 7. Server Hardware Options

The server can run on any of the following:

| Option | Vosk latency | Notes |
|---|---|---|
| Laptop (Intel i5+) | 10–20 ms | Best for demos |
| Raspberry Pi 4 (4 GB) | 30–60 ms | Portable all-in-one setup |
| Raspberry Pi 5 | 15–30 ms | Preferred for Pi deployment |
| Cloud VM (same LAN via VPN) | 20–40 ms | Adds VPN overhead |

> **Recommendation:** Use a laptop for the SIH demo — lowest Vosk latency, easiest to set up.

---

## 8. Physical Setup Checklist

- [ ] ESP32-S3 mounted on breadboard or enclosure
- [ ] INMP441 wired with correct GPIO pins (verified with multimeter)
- [ ] L/R pin tied to GND (confirm mono LEFT channel)
- [ ] USB-C connected for dev, or LiPo + TP4056 for portable
- [ ] Server laptop on same Wi-Fi network as ESP32-S3
- [ ] Server IP set in firmware (`SERVER_URI` in `main.c`)
- [ ] Firmware compiled and flashed (`idf.py build flash monitor`)
- [ ] Serial monitor shows "I2S started at 16000 Hz"
- [ ] Serial monitor shows "Pre-warmed WS → ws://..."
