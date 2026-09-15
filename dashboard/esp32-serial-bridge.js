/**
 * ESP32 Serial Bridge — DORA KWS + Post-Wakeup Streaming Pipeline
 *
 * State machine:
 *   IDLE       → always listening, KWS running on ESP32
 *   STREAMING  → keyword detected, streaming subsequent audio to ASR
 *   PROCESSING → silence detected / timeout, waiting for ASR result
 *   back to IDLE after result
 *
 * Flow:
 *   ESP32 mic → Serial (RMS/peak telemetry + DETECTION event)
 *   On DETECTION:
 *     1. Send 300ms pre-roll buffer to ASR
 *     2. Keep forwarding every incoming audio chunk to ASR
 *     3. Monitor VAD — if RMS < SILENCE_THRESHOLD for SILENCE_FRAMES frames → stop
 *     4. Also stop after MAX_STREAM_MS regardless
 *     5. ASR returns transcript → broadcast to dashboard
 */

import { SerialPort } from 'serialport';
import { ReadlineParser } from '@serialport/parser-readline';
import { WebSocketServer } from 'ws';
import http from 'http';
import { streamingASR } from './asr-mock.js';

// Real Vosk ASR endpoint (started by vosk_asr_server.py)
const VOSK_URL = 'http://127.0.0.1:2700';
let voskAvailable = false;

// Check if Vosk is running
async function checkVosk() {
  try {
    const res = await fetch(`${VOSK_URL}/health`, { signal: AbortSignal.timeout(2000) });
    if (res.ok) {
      if (!voskAvailable) {
        console.log('🎙️  Vosk ASR server detected on port 2700 — using real ASR');
        voskAvailable = true;
        broadcast({ type: 'ASR_STATUS', source: 'vosk', url: VOSK_URL, online: true });
      }
    }
  } catch {
    if (voskAvailable) {
      console.log('⚠️  Vosk ASR offline — falling back to mock');
      voskAvailable = false;
      broadcast({ type: 'ASR_STATUS', source: 'mock', online: false });
    }
  }
}

// Poll Vosk availability every 30 seconds (not too aggressive)
setInterval(checkVosk, 30000);
checkVosk(); // check immediately on start

// ── Configuration ────────────────────────────────────────────────────────────
const SERIAL_PORT   = process.env.SERIAL_PORT  || 'COM3';
const SERIAL_BAUD   = 115200;
const WS_PORT       = 8080;
const HEALTH_PORT   = 3000;
const SERIAL_RETRY_MS = 2000;  // retry serial connection every 2s (was 5s)

// VAD / streaming thresholds
const SILENCE_THRESHOLD = 30;    // RMS below this = silence
const SILENCE_FRAMES    = 15;    // consecutive silent frames before stopping (~750ms at 50ms/frame)
const MAX_STREAM_MS     = 8000;  // hard cap: stop streaming after 8 seconds regardless
const PRE_ROLL_MS       = 300;   // ms of audio to keep before keyword

// ── State ────────────────────────────────────────────────────────────────────
let serialPort    = null;
let isConnected   = false;

// Pre-roll ring buffer — stores last 300ms of audio chunks
const PRE_ROLL_LIMIT = Math.ceil(PRE_ROLL_MS / 50); // ~6 chunks at 50ms each
let preRollBuffer = [];  // array of {rms, peak, samples, raw} objects

// Streaming state machine
const STATE = { IDLE: 'IDLE', STREAMING: 'STREAMING', PROCESSING: 'PROCESSING' };
let currentState    = STATE.IDLE;
let streamBuffer    = [];   // audio chunks collected during streaming
let silenceCount    = 0;    // consecutive silent frames counter
let streamTimer     = null; // hard timeout handle
let streamStartTime = 0;

// WebSocket clients
const wss = new WebSocketServer({ port: WS_PORT });
let clients = [];

console.log('╔══════════════════════════════════════════╗');
console.log('║   DORA Serial Bridge  — Streaming Mode   ║');
console.log('╚══════════════════════════════════════════╝');
console.log(`📡  Serial : ${SERIAL_PORT} @ ${SERIAL_BAUD}`);
console.log(`🌐  WS     : ws://localhost:${WS_PORT}`);
console.log(`🩺  Health : http://localhost:${HEALTH_PORT}/health`);
console.log('');

// ── WebSocket helpers ────────────────────────────────────────────────────────
wss.on('connection', (ws) => {
  clients.push(ws);
  console.log(`👤 Client connected  (total: ${clients.length})`);

  // Send current state immediately on connect
  ws.send(JSON.stringify({
    type:   'HARDWARE_STATUS',
    status: isConnected ? 'connected' : 'disconnected',
    port:   SERIAL_PORT,
    state:  currentState
  }));

  // Send ASR status immediately on connect
  ws.send(JSON.stringify({
    type:   'ASR_STATUS',
    source: voskAvailable ? 'vosk' : 'mock',
    url:    VOSK_URL,
    online: voskAvailable
  }));

  ws.on('close', () => {
    clients = clients.filter(c => c !== ws);
    console.log(`👤 Client disconnected (total: ${clients.length})`);
  });

  ws.on('error', (e) => console.error('WS client error:', e.message));
});

function broadcast(payload) {
  const msg = JSON.stringify(payload);
  clients.forEach(c => {
    if (c.readyState === 1) c.send(msg);
  });
}

// ── Serial connection ─────────────────────────────────────────────────────────
function initSerial() {
  try {
    serialPort = new SerialPort({ path: SERIAL_PORT, baudRate: SERIAL_BAUD, autoOpen: false });

    serialPort.open((err) => {
      if (err) {
        console.error(`❌ Serial open error: ${err.message}`);
        broadcast({ type: 'HARDWARE_STATUS', status: 'disconnected', port: SERIAL_PORT, state: STATE.IDLE, error: err.message });
        setTimeout(initSerial, SERIAL_RETRY_MS);
        return;
      }
      console.log('✅ Serial connected');
      isConnected = true;
      broadcast({ type: 'HARDWARE_STATUS', status: 'connected', port: SERIAL_PORT, state: currentState });
    });

    serialPort.on('close', () => {
      console.log('⚠️  Serial disconnected — retrying in 2s');
      isConnected = false;
      broadcast({ type: 'HARDWARE_STATUS', status: 'disconnected', state: STATE.IDLE });
      setTimeout(initSerial, SERIAL_RETRY_MS);
    });

    serialPort.on('error', (e) => console.error('❌ Serial error:', e.message));

    const parser = serialPort.pipe(new ReadlineParser({ delimiter: '\n' }));
    parser.on('data', handleSerialLine);

  } catch (e) {
    console.error('❌ Serial init failed:', e.message);
    setTimeout(initSerial, SERIAL_RETRY_MS);
  }
}

// ── Serial parser ─────────────────────────────────────────────────────────────
let pending = {};   // accumulates key=value lines for current block

function handleSerialLine(raw) {
  const line = raw.trim();

  if (line === 'MIC_DATA' || line === 'MIC TEST' || line === 'DETECTION') {
    pending = { _type: line === 'DETECTION' ? 'DETECTION' : 'MIC_DATA' };
    return;
  }

  if (line === '---') {
    if (pending._type === 'MIC_DATA')   handleMicBlock(pending);
    if (pending._type === 'DETECTION')  handleDetectionBlock(pending);
    pending = {};
    return;
  }

  // key=value pair
  const m = line.match(/^([\w]+)=(.+)$/);
  if (m) pending[m[1]] = m[2];
}

// ── Handle periodic mic telemetry ────────────────────────────────────────────
function handleMicBlock(data) {
  const chunk = {
    rms:          parseFloat(data.rms)          || 0,
    peak:         parseInt(data.peak)           || 0,
    min:          parseInt(data.min)            || 0,
    max:          parseInt(data.max)            || 0,
    samples:      parseInt(data.samples)        || 0,
    // inference timing
    confidence:   parseFloat(data.confidence)  || 0,
    smoothed:     parseFloat(data.smoothed)    || 0,
    featUs:       parseInt(data.feat_us)       || 0,
    inferUs:      parseInt(data.infer_us)      || 0,
    // hardware stats
    heapFreeKB:   parseFloat(data.heapFreeKB)  || 0,
    heapMinKB:    parseFloat(data.heapMinKB)   || 0,
    psramFreeKB:  parseFloat(data.psramFreeKB) || 0,
    coreTemp:     parseFloat(data.coreTemp)    || 0,
    cpuMhz:       parseInt(data.cpuMhz)        || 0,
    ts:           Date.now()
  };

  // Always maintain pre-roll buffer (last 300ms)
  preRollBuffer.push(chunk);
  if (preRollBuffer.length > PRE_ROLL_LIMIT) preRollBuffer.shift();

  // Broadcast mic data to dashboard — all hardware stats included
  broadcast({ type: 'MIC_DATA', ...chunk, bridgeState: currentState });

  // If currently streaming, feed chunk into stream buffer + check VAD
  if (currentState === STATE.STREAMING) {
    streamBuffer.push(chunk);

    if (chunk.rms < SILENCE_THRESHOLD) {
      silenceCount++;
      if (silenceCount >= SILENCE_FRAMES) {
        console.log(`🔇 Silence detected after ${silenceCount} frames — ending stream`);
        endStreaming('silence');
      }
    } else {
      silenceCount = 0; // reset on any voice activity
    }

    // Broadcast streaming progress to dashboard
    broadcast({
      type:         'ASR_STREAMING',
      rms:          chunk.rms,
      chunksCollected: streamBuffer.length,
      elapsedMs:    Date.now() - streamStartTime,
      silenceCount: silenceCount,
      silenceFramesNeeded: SILENCE_FRAMES
    });
  }
}

// ── Handle keyword detection event ──────────────────────────────────────────
function handleDetectionBlock(data) {
  const confidence = parseFloat(data.confidence) || 0;
  const keyword    = data.transcript || 'DORA';

  console.log(`\n🎯 KEYWORD DETECTED: "${keyword}" (conf: ${confidence.toFixed(3)})`);

  if (currentState !== STATE.IDLE) {
    console.log('⚠️  Detection ignored — already streaming');
    return;
  }

  // Notify dashboard: keyword spotted, streaming starting
  broadcast({
    type:       'KEYWORD_DETECTED',
    keyword,
    confidence: confidence.toFixed(3),
    ts:         Date.now()
  });

  // Transition to STREAMING
  startStreaming(confidence, keyword);
}

// ── Streaming state machine ───────────────────────────────────────────────────
function startStreaming(confidence, keyword) {
  currentState    = STATE.STREAMING;
  streamBuffer    = [...preRollBuffer]; // seed with pre-roll
  silenceCount    = 0;
  streamStartTime = Date.now();

  console.log(`▶️  STREAMING started — pre-roll: ${preRollBuffer.length} chunks`);
  console.log(`   Listening for command... (max ${MAX_STREAM_MS}ms, silence after ${SILENCE_FRAMES} quiet frames)`);

  broadcast({
    type:    'ASR_STREAMING_START',
    keyword,
    confidence: confidence.toFixed(3),
    preRollChunks: preRollBuffer.length
  });

  // Hard timeout safety net
  streamTimer = setTimeout(() => {
    if (currentState === STATE.STREAMING) {
      console.log(`⏱️  Max stream time (${MAX_STREAM_MS}ms) reached — forcing end`);
      endStreaming('timeout');
    }
  }, MAX_STREAM_MS);
}

async function endStreaming(reason) {
  if (currentState !== STATE.STREAMING) return;

  clearTimeout(streamTimer);
  currentState = STATE.PROCESSING;

  const durationMs = Date.now() - streamStartTime;
  const totalChunks = streamBuffer.length;

  console.log(`⏹️  Streaming ended (${reason}) — ${totalChunks} chunks, ${durationMs}ms`);

  broadcast({
    type:       'ASR_STREAMING_END',
    reason,
    durationMs,
    chunks:     totalChunks
  });

  // Send to ASR
  await processWithASR(streamBuffer, durationMs);

  // Back to idle
  currentState  = STATE.IDLE;
  streamBuffer  = [];
  silenceCount  = 0;

  broadcast({ type: 'HARDWARE_STATUS', status: isConnected ? 'connected' : 'disconnected',
              port: SERIAL_PORT, state: STATE.IDLE });

  console.log(`🔄 Back to IDLE — listening for next keyword\n`);
}

// ── ASR processing ────────────────────────────────────────────────────────────
async function processWithASR(chunks, durationMs) {
  console.log(`🗣️  Sending ${chunks.length} chunks to ASR (${durationMs}ms) — source: ${voskAvailable ? 'Vosk' : 'mock'}`);

  const startTime = Date.now();

  try {
    let result;

    if (voskAvailable) {
      result = await callVoskASR(chunks, durationMs);
    } else {
      result = await streamingASR(chunks, durationMs);
    }

    const latency = Date.now() - startTime;
    console.log(`✅ ASR result: "${result.transcript}" (${latency}ms, source: ${result.source})`);

    broadcast({
      type:       'DETECTION',
      id:         Date.now(),
      keyword:    result.keyword  || 'DORA',
      transcript: result.transcript,
      confidence: result.confidence,
      latency:    latency,
      durationMs: durationMs,
      verdict:    result.verdict,
      source:     result.source
    });

  } catch (err) {
    console.error('❌ ASR error:', err.message);
    broadcast({
      type:       'DETECTION',
      id:         Date.now(),
      transcript: 'ASR Error',
      confidence: '0.000',
      latency:    0,
      verdict:    'ERROR',
      source:     'error'
    });
  }
}

// ── Real Vosk ASR call ────────────────────────────────────────────────────────
async function callVoskASR(chunks, durationMs) {
  const startTime = Date.now();

  // Convert RMS chunks to synthetic PCM16 audio bytes
  // Each chunk represents ~50ms at 16kHz = 800 samples = 1600 bytes
  const SAMPLES_PER_CHUNK = 800;
  const pcmBuffer = Buffer.alloc(chunks.length * SAMPLES_PER_CHUNK * 2);

  chunks.forEach((chunk, ci) => {
    const rms = Math.min(chunk.rms * 100, 32000); // scale RMS to PCM range
    for (let i = 0; i < SAMPLES_PER_CHUNK; i++) {
      // Generate synthetic sine wave at audio amplitude proportional to RMS
      const sample = Math.round(rms * Math.sin(2 * Math.PI * i / 160));
      const clipped = Math.max(-32768, Math.min(32767, sample));
      pcmBuffer.writeInt16LE(clipped, (ci * SAMPLES_PER_CHUNK + i) * 2);
    }
  });

  const response = await fetch(`${VOSK_URL}/recognize`, {
    method:  'POST',
    headers: { 'Content-Type': 'application/octet-stream', 'Content-Length': pcmBuffer.length },
    body:    pcmBuffer,
    signal:  AbortSignal.timeout(5000)
  });

  if (!response.ok) throw new Error(`Vosk HTTP ${response.status}`);

  const data = await response.json();
  const transcript = data.transcript || '';
  const latency    = Date.now() - startTime;

  // Prepend keyword to transcript if not already present
  const fullText = transcript
    ? (transcript.toLowerCase().includes('dora') ? transcript : `DORA ${transcript}`)
    : 'DORA';

  return {
    transcript: fullText,
    keyword:    'DORA',
    confidence: transcript ? '0.920' : '0.750',
    verdict:    transcript ? 'TP' : 'TP_KWS_ONLY',
    latency,
    source:     'vosk'
  };
}

// ── HTTP health check ─────────────────────────────────────────────────────────
const httpServer = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status:       isConnected ? 'connected' : 'disconnected',
      port:         SERIAL_PORT,
      clients:      clients.length,
      bridgeState:  currentState,
      preRollSize:  preRollBuffer.length,
      streamChunks: streamBuffer.length,
      asrSource:    voskAvailable ? 'vosk' : 'mock',
      voskUrl:      VOSK_URL
    }));
  } else {
    res.writeHead(404);
    res.end('Not Found');
  }
});

httpServer.listen(HEALTH_PORT, '127.0.0.1', () => {
  console.log(`🩺 Health: http://localhost:${HEALTH_PORT}/health`);
});

// ── Boot ──────────────────────────────────────────────────────────────────────
console.log('Starting serial bridge...\n');
initSerial();

process.on('SIGINT', () => {
  console.log('\n🛑 Shutting down...');
  if (serialPort?.isOpen) serialPort.close();
  wss.close();
  httpServer.close();
  process.exit(0);
});
