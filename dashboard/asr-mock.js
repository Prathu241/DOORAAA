/**
 * ASR Mock Service — Streaming-aware
 *
 * Simulates a real Vosk/cloud ASR that receives a stream of audio chunks
 * after keyword detection and returns a transcript.
 *
 * In production, replace streamingASR() with a real WebSocket connection
 * to a Vosk server:
 *   wss://your-vosk-server/asr
 *   Send PCM16 chunks → receive partial/final transcript JSON
 *
 * Mock logic:
 *   - Analyses the RMS energy profile of the streamed chunks
 *   - Higher average RMS + longer duration = higher confidence command
 *   - Returns realistic latency (network + decode simulation)
 */

// Commands the mock ASR can "recognise" after the keyword
const COMMANDS = [
  { text: 'turn on the lights',    minRms: 80,  minDuration: 800  },
  { text: 'start the system',      minRms: 70,  minDuration: 600  },
  { text: 'run diagnostics',       minRms: 60,  minDuration: 700  },
  { text: 'status report',         minRms: 50,  minDuration: 500  },
  { text: 'confirm sequence',      minRms: 75,  minDuration: 900  },
  { text: 'initiate launch check', minRms: 90,  minDuration: 1200 },
  { text: 'abort mission',         minRms: 85,  minDuration: 800  },
  { text: 'read telemetry',        minRms: 55,  minDuration: 600  },
];

/**
 * streamingASR(chunks, durationMs)
 *
 * @param {Array}  chunks     - Array of mic data objects {rms, peak, min, max, ts}
 *                              These are the audio frames captured AFTER keyword detection
 * @param {number} durationMs - Total duration of the streamed audio in ms
 * @returns {Promise<{transcript, keyword, confidence, verdict, latency, source}>}
 */
export async function streamingASR(chunks, durationMs) {
  const startTime = Date.now();

  // ── Analyse the audio stream ───────────────────────────────────────────────
  const voiceChunks = chunks.filter(c => c.rms > 20); // filter near-silent frames
  const avgRms      = voiceChunks.length > 0
    ? voiceChunks.reduce((s, c) => s + c.rms, 0) / voiceChunks.length
    : 0;
  const peakRms     = Math.max(...chunks.map(c => c.rms), 0);
  const voiceRatio  = chunks.length > 0 ? voiceChunks.length / chunks.length : 0;

  console.log(`   [ASR] chunks=${chunks.length}, voiceChunks=${voiceChunks.length}, avgRms=${avgRms.toFixed(1)}, duration=${durationMs}ms`);

  // ── Simulate network + decode latency ─────────────────────────────────────
  // Real Vosk over LAN: ~100-300ms
  // We simulate: 80ms base + proportional to audio length
  const mockLatency = 80 + Math.min(200, durationMs * 0.05) + Math.random() * 50;
  await sleep(mockLatency);

  // ── Determine if a command was spoken ─────────────────────────────────────
  // Conditions for a valid command:
  //   1. Enough voice activity (voiceRatio > 0.3)
  //   2. Minimum average RMS (some volume)
  //   3. Minimum duration (at least 400ms of audio after keyword)
  const hasVoiceActivity = voiceRatio > 0.3 && avgRms > 40 && durationMs > 400;

  if (!hasVoiceActivity) {
    // No command spoken after keyword — common case (false trigger or standalone keyword)
    const latency = Date.now() - startTime;
    console.log(`   [ASR] No command detected (voiceRatio=${voiceRatio.toFixed(2)}, avgRms=${avgRms.toFixed(1)})`);
    return {
      transcript: '',
      keyword:    'DORA',
      confidence: (0.5 + Math.random() * 0.2).toFixed(3),
      verdict:    'TP_KWS_ONLY',   // keyword detected, no follow-up command
      latency,
      source:     'mock'
    };
  }

  // ── Pick a plausible command based on audio characteristics ───────────────
  const eligible = COMMANDS.filter(
    cmd => avgRms >= cmd.minRms && durationMs >= cmd.minDuration
  );

  let chosenCommand;
  if (eligible.length > 0) {
    // Pick randomly from eligible commands
    chosenCommand = eligible[Math.floor(Math.random() * eligible.length)];
  } else {
    // Fallback — audio present but low energy
    chosenCommand = { text: 'unrecognised command' };
  }

  // ── Confidence scoring ─────────────────────────────────────────────────────
  // Higher RMS + longer speech + more voice activity → higher confidence
  const rawConf = Math.min(0.99,
    0.55
    + (Math.min(avgRms, 300) / 300) * 0.25
    + voiceRatio * 0.15
    + (Math.min(durationMs, 3000) / 3000) * 0.05
  );
  const confidence = rawConf.toFixed(3);

  const verdict  = parseFloat(confidence) > 0.70 ? 'TP' : 'FP';
  const latency  = Date.now() - startTime;
  const fullText = `DORA ${chosenCommand.text}`;

  console.log(`   [ASR] ✅ "${fullText}" | conf=${confidence} | verdict=${verdict} | latency=${latency}ms`);

  return {
    transcript: fullText,
    keyword:    'DORA',
    confidence,
    verdict,
    latency,
    source:     'mock'
  };
}

/**
 * Legacy single-shot mockASR — kept for backward compatibility
 */
export function mockASR(audioBuffer, confidence) {
  const latency = Math.round(Math.random() * 100 + 50);
  if (confidence > 150) {
    return { transcript: 'DORA', latency, result: true,  confidence: (0.85 + Math.random() * 0.14).toFixed(2) };
  } else if (confidence > 100) {
    return { transcript: 'DORA', latency, result: true,  confidence: (0.70 + Math.random() * 0.20).toFixed(2) };
  }
  return   { transcript: 'Background noise', latency, result: false, confidence: '0.35' };
}

// ── Utility ───────────────────────────────────────────────────────────────────
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
