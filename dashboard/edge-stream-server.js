/**
 * DORA production edge stream gateway.
 *
 * ESP32 clients connect to ws://<PC-LAN-IP>:8765/edge and send a JSON start
 * message, real PCM16 binary frames, then a JSON end message. Dashboard
 * clients keep using ws://localhost:8080. The gateway relays device telemetry
 * and real stream lifecycle events to the dashboard, then sends the exact
 * captured PCM bytes to the local Vosk HTTP service for a final transcript.
 *
 * This is intentionally separate from esp32-serial-bridge.js: serial remains
 * a USB debugging path and must not be mistaken for cloud audio transport.
 */
import http from 'http';
import { WebSocketServer, WebSocket } from 'ws';

const EDGE_PORT = Number(process.env.EDGE_PORT || 8765);
const DASHBOARD_PORT = Number(process.env.DASHBOARD_WS_PORT || 8080);
const VOSK_URL = process.env.VOSK_URL || 'http://127.0.0.1:2700/recognize';
const VOSK_HEALTH_URL = process.env.VOSK_HEALTH_URL || 'http://127.0.0.1:2700/health';

const dashboardWss = new WebSocketServer({ port: DASHBOARD_PORT });
const edgeServer = http.createServer();
const edgeWss = new WebSocketServer({ noServer: true });

let isDeviceConnected = false;
let activePeer = null;
let lastTelemetry = null;
let isVoskOnline = false;

function broadcast(message) {
  const encoded = JSON.stringify(message);
  for (const client of dashboardWss.clients) {
    if (client.readyState === WebSocket.OPEN) client.send(encoded);
  }
}

async function checkVosk() {
  try {
    const res = await fetch(VOSK_HEALTH_URL, { signal: AbortSignal.timeout(2000) });
    const data = await res.json();
    isVoskOnline = (data.status === 'ready');
  } catch {
    isVoskOnline = false;
  }
  broadcast({ type: 'ASR_STATUS', online: isVoskOnline, url: VOSK_URL, source: 'vosk' });
  return isVoskOnline;
}

// Check Vosk on startup and every 10 seconds
checkVosk();
setInterval(checkVosk, 10000);

dashboardWss.on('connection', (socket) => {
  console.log(`[Dashboard] Client connected (${dashboardWss.clients.size} total)`);
  // Send current hardware status immediately
  socket.send(JSON.stringify({
    type: 'HARDWARE_STATUS',
    status: isDeviceConnected ? 'connected' : 'waiting',
    transport: 'wifi',
    peer: activePeer
  }));
  // Send current ASR status
  socket.send(JSON.stringify({
    type: 'ASR_STATUS',
    online: isVoskOnline,
    url: VOSK_URL,
    source: 'vosk'
  }));
  // Replay last telemetry if available so widgets don't wait
  if (lastTelemetry) {
    socket.send(JSON.stringify(lastTelemetry));
  }
});

edgeServer.on('upgrade', (request, socket, head) => {
  if (request.url !== '/edge') {
    console.warn(`[Edge] Rejected upgrade request on path: ${request.url}`);
    return socket.destroy();
  }
  edgeWss.handleUpgrade(request, socket, head, (ws) => edgeWss.emit('connection', ws, request));
});

edgeWss.on('connection', (socket, request) => {
  const peer = request.socket.remoteAddress;
  activePeer = peer;
  isDeviceConnected = true;
  let session = null;
  console.log(`[Edge] ESP32 connected from ${peer}`);
  broadcast({ type: 'HARDWARE_STATUS', status: 'connected', transport: 'wifi', peer });

  socket.on('message', async (data, isBinary) => {
    if (isBinary) {
      if (!session) return;
      const frame = Buffer.from(data);
      session.frames.push(frame);
      session.bytes += frame.length;
      if (!session.firstByteAt) {
        session.firstByteAt = Date.now();
        console.log(`[Edge] First audio byte received for session ${session.id}`);
        broadcast({
          type: 'ASR_FIRST_AUDIO_RECEIVED',
          sessionId: session.id,
          serverReceivedAtMs: session.firstByteAt,
          keywordEndDeviceMs: session.keywordEndDeviceMs
        });
      }
      return;
    }

    let message;
    const rawText = data.toString();
    try {
      message = JSON.parse(rawText);
    } catch {
      return console.warn('[Edge] Ignoring malformed device JSON:', rawText.slice(0, 100));
    }

    if (message.type === 'telemetry') {
      // NOTE: spread message first, then enforce type: 'MIC_DATA' so it's not overwritten
      const telemetryPayload = {
        ...message,
        type: 'MIC_DATA',
        bridgeState: session ? 'STREAMING' : 'IDLE'
      };
      lastTelemetry = telemetryPayload;
      broadcast(telemetryPayload);
      return;
    }

    if (message.type === 'start') {
      if (session) return;
      session = {
        id: message.sessionId || `${Date.now()}`,
        keyword: message.keyword || 'DORA',
        confidence: Number(message.confidence || 0),
        keywordEndDeviceMs: Number(message.keywordEndDeviceMs || 0),
        frames: [], bytes: 0, firstByteAt: 0, startedAt: Date.now()
      };
      console.log(`[Edge] KWS Triggered: "${session.keyword}" (conf: ${session.confidence.toFixed(3)})`);
      broadcast({ type: 'KEYWORD_DETECTED', keyword: session.keyword,
        confidence: session.confidence.toFixed(3), ts: session.startedAt });
      broadcast({ type: 'ASR_STREAMING_START', keyword: session.keyword,
        confidence: session.confidence.toFixed(3), preRollMs: Number(message.preRollMs || 0) });
      return;
    }

    if (message.type === 'end' && session) {
      const finished = session;
      session = null;
      const durationMs = Date.now() - finished.startedAt;
      console.log(`[Edge] Audio stream ended: ${finished.bytes} bytes across ${finished.frames.length} frames in ${durationMs}ms`);
      broadcast({ type: 'ASR_STREAMING_END', reason: message.reason || 'device_end', durationMs,
        bytes: finished.bytes, chunks: finished.frames.length });
      await recogniseAndBroadcast(finished, durationMs);
    }
  });

  socket.on('close', () => {
    console.log(`[Edge] ESP32 disconnected (${peer})`);
    isDeviceConnected = false;
    activePeer = null;
    broadcast({ type: 'HARDWARE_STATUS', status: 'disconnected', transport: 'wifi' });
  });

  socket.on('error', (err) => {
    console.error(`[Edge] Socket error (${peer}):`, err.message);
  });
});

async function recogniseAndBroadcast(session, durationMs) {
  const startedAt = Date.now();
  const pcm = Buffer.concat(session.frames);
  console.log(`[Vosk] Sending ${pcm.length} bytes PCM to Vosk at ${VOSK_URL}...`);
  try {
    const response = await fetch(VOSK_URL, { method: 'POST',
      headers: { 'Content-Type': 'application/octet-stream' }, body: pcm,
      signal: AbortSignal.timeout(15000) });
    if (!response.ok) throw new Error(`Vosk HTTP ${response.status}`);
    const result = await response.json();
    const transcript = result.transcript || '';
    const latency = Date.now() - startedAt;
    console.log(`[Vosk] Result: "${transcript}" (latency: ${latency}ms)`);
    broadcast({ type: 'DETECTION', id: Date.now(), keyword: session.keyword,
      transcript, confidence: session.confidence.toFixed(3), latency,
      durationMs, verdict: transcript ? 'TP' : 'TP_KWS_ONLY', source: 'vosk',
      audioBytes: session.bytes });
  } catch (error) {
    console.error('[Vosk] Error:', error.message);
    broadcast({ type: 'DETECTION', id: Date.now(), keyword: session.keyword,
      transcript: 'ASR Error', confidence: session.confidence.toFixed(3), latency: 0,
      verdict: 'ERROR', source: 'vosk', error: error.message });
  }
}

edgeServer.listen(EDGE_PORT, '0.0.0.0', () => {
  console.log(`DORA edge input: ws://0.0.0.0:${EDGE_PORT}/edge`);
  console.log(`Dashboard events: ws://localhost:${DASHBOARD_PORT}`);
  console.log(`Vosk target: ${VOSK_URL}`);
});
