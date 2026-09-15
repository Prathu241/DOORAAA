// Copy this file to secrets.h and fill in values for the network that hosts
// dashboard/edge-stream-server.js. Do not commit secrets.h.
#pragma once

#define DORA_WIFI_SSID "YOUR_WIFI_NAME"
#define DORA_WIFI_PASSWORD "YOUR_WIFI_PASSWORD"

// Use the LAN IPv4 address of the computer running the edge stream server.
// Do not use localhost: from an ESP32, localhost means the ESP32 itself.
#define DORA_CLOUD_HOST "192.168.1.100"
#define DORA_CLOUD_PORT 8765
#define DORA_CLOUD_PATH "/edge"
