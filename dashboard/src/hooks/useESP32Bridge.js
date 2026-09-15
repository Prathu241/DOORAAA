/**
 * useESP32Bridge — React hook for ESP32 serial bridge WebSocket
 *
 * Handles all message types from the streaming pipeline:
 *   HARDWARE_STATUS     → connection state
 *   MIC_DATA            → live mic telemetry (rms, peak, samples)
 *   KEYWORD_DETECTED    → KWS fired, keyword confirmed
 *   ASR_STREAMING_START → post-wakeup streaming begun
 *   ASR_STREAMING       → per-chunk progress during streaming
 *   ASR_STREAMING_END   → streaming stopped (silence/timeout)
 *   DETECTION           → final ASR result with transcript + verdict
 */

import { useEffect, useState, useRef, useCallback } from 'react';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080';

// Bridge states (mirrors server state machine)
export const BRIDGE_STATE = {
  IDLE:       'IDLE',
  STREAMING:  'STREAMING',
  PROCESSING: 'PROCESSING'
};

export function useESP32Bridge() {
  // ── Connection ─────────────────────────────────────────────────────────────
  const [isConnected,     setIsConnected]     = useState(false);
  const [hardwareStatus,  setHardwareStatus]  = useState('disconnected');

  // ── ASR status ─────────────────────────────────────────────────────────────
  const [asrStatus, setAsrStatus] = useState({
    source: 'mock', online: false, url: ''
  });

  // ── Mic telemetry ──────────────────────────────────────────────────────────
  const [micData, setMicData] = useState({
    rms: 0, peak: 0, min: 0, max: 0, samples: 0, bufferSize: 0,
    // inference timing
    confidence: 0, smoothed: 0, featUs: 0, inferUs: 0,
    // hardware stats
    heapFreeKB: 0, heapMinKB: 0, psramFreeKB: 0, coreTemp: 0, cpuMhz: 0, cpuUtil: 0
  });

  // ── Pipeline state machine ─────────────────────────────────────────────────
  const [bridgeState,   setBridgeState]   = useState(BRIDGE_STATE.IDLE);

  // KEYWORD_DETECTED payload
  const [lastKeyword, setLastKeyword] = useState({
    keyword: '', confidence: '0.000', ts: null
  });

  // ASR_STREAMING_START payload
  const [streamingInfo, setStreamingInfo] = useState({
    active:        false,
    keyword:       '',
    confidence:    '0.000',
    preRollChunks: 0,
    startTs:       null
  });

  // ASR_STREAMING per-chunk progress
  const [streamingProgress, setStreamingProgress] = useState({
    rms:                 0,
    chunksCollected:     0,
    elapsedMs:           0,
    silenceCount:        0,
    silenceFramesNeeded: 15
  });

  // ASR_STREAMING_END
  const [streamingEnd, setStreamingEnd] = useState({
    reason: '', durationMs: 0, chunks: 0
  });

  // ── Detection log ──────────────────────────────────────────────────────────
  const [detections, setDetections] = useState([]);

  // ── Last transcript (most recent ASR result) ───────────────────────────────
  const [lastTranscript, setLastTranscript] = useState({
    text:       '',
    confidence: '0.000',
    verdict:    '',
    latency:    0,
    durationMs: 0,
    ts:         null
  });

  // ── WebSocket lifecycle ───────────────────────────────────────────────────
  const wsRef             = useRef(null);
  const reconnectRef      = useRef(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('✅ Bridge WebSocket connected');
        setIsConnected(true);
        if (reconnectRef.current) {
          clearTimeout(reconnectRef.current);
          reconnectRef.current = null;
        }
      };

      ws.onmessage = (evt) => {
        let msg;
        try { msg = JSON.parse(evt.data); }
        catch { return; }

        switch (msg.type) {

          // ── ASR status update ─────────────────────────────────────────
          case 'ASR_STATUS':
            setAsrStatus({
              source: msg.source || 'mock',
              online: msg.online || false,
              url:    msg.url    || ''
            });
            break;

          // ── Hardware connection status ──────────────────────────────────
          case 'HARDWARE_STATUS':
            setHardwareStatus(msg.status);
            if (msg.state) setBridgeState(msg.state);
            break;

          // ── Live mic telemetry ─────────────────────────────────────────
          case 'MIC_DATA':
          case 'telemetry':
            setMicData((prev) => ({
              rms:         msg.rms         ?? prev.rms,
              peak:        msg.peak        ?? prev.peak,
              min:         msg.min         ?? prev.min,
              max:         msg.max         ?? prev.max,
              samples:     msg.samples     ?? (prev.samples + 160),
              bufferSize:  msg.bufferSize  ?? prev.bufferSize,
              // inference timing
              confidence:  msg.confidence  ?? prev.confidence,
              smoothed:    msg.smoothed    ?? prev.smoothed,
              featUs:      msg.featUs      ?? prev.featUs,
              inferUs:     msg.inferUs     ?? prev.inferUs,
              // hardware stats
              heapFreeKB:  msg.heapFreeKB  ?? prev.heapFreeKB,
              heapMinKB:   msg.heapMinKB   ?? prev.heapMinKB,
              psramFreeKB: msg.psramFreeKB ?? prev.psramFreeKB,
              coreTemp:    msg.coreTemp    ?? prev.coreTemp,
              cpuMhz:      msg.cpuMhz      ?? prev.cpuMhz,
              cpuUtil:     msg.cpuUtil     ?? prev.cpuUtil,
            }));
            if (msg.bridgeState) setBridgeState(msg.bridgeState);
            break;

          // ── KWS fired ─────────────────────────────────────────────────
          case 'KEYWORD_DETECTED':
            setLastKeyword({
              keyword:    msg.keyword,
              confidence: msg.confidence,
              ts:         msg.ts || Date.now()
            });
            setBridgeState(BRIDGE_STATE.STREAMING);
            break;

          // ── Post-wakeup streaming started ─────────────────────────────
          case 'ASR_STREAMING_START':
            setStreamingInfo({
              active:        true,
              keyword:       msg.keyword,
              confidence:    msg.confidence,
              preRollChunks: msg.preRollChunks || 0,
              startTs:       Date.now()
            });
            setBridgeState(BRIDGE_STATE.STREAMING);
            break;

          // ── Per-chunk streaming progress ──────────────────────────────
          case 'ASR_STREAMING':
            setStreamingProgress({
              rms:                 msg.rms             || 0,
              chunksCollected:     msg.chunksCollected || 0,
              elapsedMs:           msg.elapsedMs       || 0,
              silenceCount:        msg.silenceCount    || 0,
              silenceFramesNeeded: msg.silenceFramesNeeded || 15
            });
            break;

          // ── Streaming ended, waiting for ASR result ───────────────────
          case 'ASR_STREAMING_END':
            setStreamingInfo(prev => ({ ...prev, active: false }));
            setStreamingEnd({
              reason:     msg.reason     || '',
              durationMs: msg.durationMs || 0,
              chunks:     msg.chunks     || 0
            });
            setBridgeState(BRIDGE_STATE.PROCESSING);
            break;

          // ── Final ASR result ──────────────────────────────────────────
          case 'DETECTION': {
            const entry = {
              id:         msg.id || Date.now(),
              time:       new Date().toLocaleTimeString('en-IN', { hour12: false }),
              keyword:    msg.keyword    || 'DORA',
              transcript: msg.transcript || '',
              confidence: msg.confidence || '0.000',
              latency:    msg.latency    || 0,
              durationMs: msg.durationMs || 0,
              verdict:    msg.verdict    || 'TP',
              source:     msg.source     || 'mock'
            };

            setLastTranscript({
              text:       entry.transcript,
              confidence: entry.confidence,
              verdict:    entry.verdict,
              latency:    entry.latency,
              durationMs: entry.durationMs,
              ts:         Date.now()
            });

            setDetections(prev => [entry, ...prev].slice(0, 20));
            setBridgeState(BRIDGE_STATE.IDLE);
            setStreamingInfo(prev => ({ ...prev, active: false }));
            break;
          }

          default:
            break;
        }
      };

      ws.onerror = () => {
        setIsConnected(false);
      };

      ws.onclose = () => {
        setIsConnected(false);
        setBridgeState(BRIDGE_STATE.IDLE);
        console.log('WebSocket closed — reconnecting in 3s');
        reconnectRef.current = setTimeout(connect, 3000);
      };

    } catch (err) {
      console.warn('WebSocket connect failed:', err.message);
      reconnectRef.current = setTimeout(connect, 3000);
    }
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on unmount
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    // Connection
    isConnected,
    hardwareStatus,

    // ASR status
    asrStatus,          // { source: 'vosk'|'mock', online: bool, url: string }

    // Pipeline state
    bridgeState,        // 'IDLE' | 'STREAMING' | 'PROCESSING'

    // Mic data
    micData,

    // Keyword detection
    lastKeyword,        // { keyword, confidence, ts }

    // Streaming progress
    streamingInfo,      // { active, keyword, confidence, preRollChunks, startTs }
    streamingProgress,  // { rms, chunksCollected, elapsedMs, silenceCount, ... }
    streamingEnd,       // { reason, durationMs, chunks }

    // Results
    lastTranscript,     // { text, confidence, verdict, latency, durationMs, ts }
    detections          // array of last 20 detection entries
  };
}
