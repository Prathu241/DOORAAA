/**
 * ESP32 Serial Bridge - WebSocket Server
 * Reads serial data from ESP32 and broadcasts to dashboard via WebSocket
 */

import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import { WebSocketServer } from 'ws';

const SERIAL_PORT = process.env.ESP32_PORT || 'COM10'; // Use the correct port
const SERIAL_BAUD = 115200;
const WS_PORT = 8080;

console.log('🔧 ESP32 Serial Bridge starting...');

// Create WebSocket server
const wss = new WebSocketServer({ port: WS_PORT });
let clients = [];

wss.on('connection', (ws) => {
  console.log('✅ Dashboard connected');
  clients.push(ws);

  ws.on('close', () => {
    clients = clients.filter(c => c !== ws);
    console.log('❌ Dashboard disconnected');
  });
});

// Broadcast to all connected clients
function broadcast(data) {
  const message = JSON.stringify(data);
  clients.forEach(client => {
    if (client.readyState === 1) { // WebSocket.OPEN
      client.send(message);
    }
  });
}

// Connect to ESP32 serial port
try {
  const port = new SerialPort({
    path: SERIAL_PORT,
    baudRate: SERIAL_BAUD,
  });

  const parser = port.pipe(new ReadlineParser({ delimiter: '\n' }));

  port.on('open', () => {
    console.log(`✅ Connected to ESP32 on ${SERIAL_PORT} @ ${SERIAL_BAUD} baud`);
    broadcast({
      type: 'HARDWARE_STATUS',
      status: 'connected',
      port: SERIAL_PORT
    });
  });

  port.on('error', (err) => {
    console.error('❌ Serial port error:', err.message);
    broadcast({
      type: 'HARDWARE_STATUS',
      status: 'error',
      error: err.message
    });
  });

  // Parse incoming serial data
  parser.on('data', (line) => {
    const trimmed = line.trim();
    
    // Skip empty lines and headers
    if (!trimmed || trimmed.startsWith('=') || trimmed.startsWith('✓')) {
      return;
    }

    // Parse MIC TEST output format:
    // samples=18176
    // rms=1.0
    // peak=1
    // min=-1
    // max=-1
    
    if (trimmed.startsWith('samples=')) {
      const samples = parseInt(trimmed.split('=')[1]);
      broadcast({
        type: 'MIC_DATA',
        samples: samples,
        timestamp: Date.now()
      });
    } else if (trimmed.startsWith('rms=')) {
      const rms = parseFloat(trimmed.split('=')[1]);
      broadcast({
        type: 'MIC_DATA',
        rms: rms,
        timestamp: Date.now()
      });
    } else if (trimmed.startsWith('peak=')) {
      const peak = parseInt(trimmed.split('=')[1]);
      broadcast({
        type: 'MIC_DATA',
        peak: peak,
        timestamp: Date.now()
      });
    } else if (trimmed.startsWith('min=')) {
      const min = parseInt(trimmed.split('=')[1]);
      broadcast({
        type: 'MIC_DATA',
        min: min,
        timestamp: Date.now()
      });
    } else if (trimmed.startsWith('max=')) {
      const max = parseInt(trimmed.split('=')[1]);
      broadcast({
        type: 'MIC_DATA',
        max: max,
        timestamp: Date.now()
      });
    } else {
      // Forward any other messages as log
      console.log(`[ESP32] ${trimmed}`);
    }
  });

  console.log(`🌐 WebSocket server listening on ws://localhost:${WS_PORT}`);
  console.log('📡 Waiting for ESP32 data...');

} catch (err) {
  console.error('❌ Failed to connect to serial port:', err.message);
  console.error('   Make sure:');
  console.error(`   1. ESP32 is plugged in on ${SERIAL_PORT}`);
  console.error('   2. Arduino Serial Monitor is CLOSED');
  console.error('   3. No other program is using the port');
  process.exit(1);
}
