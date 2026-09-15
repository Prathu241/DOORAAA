import { useState, useEffect, useRef } from "react";
import { useESP32Bridge, BRIDGE_STATE } from "./hooks/useESP32Bridge";

// ─── Types ────────────────────────────────────────────────────────────────────
const LABEL_COLORS: Record<string, string> = {
  TP:            "#22C55E",
  FP:            "#EF4444",
  TP_KWS_ONLY:   "#38BDF8",
  ERROR:         "#F59E0B",
  IDLE:          "#64748B",
};

function fmtUptime(s: number) {
  const h = Math.floor(s / 3600).toString().padStart(2, "0");
  const m = Math.floor((s % 3600) / 60).toString().padStart(2, "0");
  const sec = (s % 60).toString().padStart(2, "0");
  return `${h}:${m}:${sec}`;
}

// ─── Live Clock ───────────────────────────────────────────────────────────────
function LiveClock({ dark }: { dark: boolean }) {
  const [now, setNow] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const date = now.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  const time = now.toLocaleTimeString("en-GB", { hour12: false });
  return (
    <div className="flex flex-col items-end">
      <span className="font-mono text-base font-bold leading-none tracking-widest">{time}</span>
      <span className={`font-mono text-[10px] ${dark ? "opacity-50" : "text-[#64748B]"}`}>{date}</span>
    </div>
  );
}

// ─── Progress Bar ─────────────────────────────────────────────────────────────
function ProgressBar({ value, max, warn = 70, danger = 90, dark }: {
  value: number; max: number; warn?: number; danger?: number; dark?: boolean;
}) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= danger ? "#EF4444" : pct >= warn ? "#F59E0B" : "#38BDF8";
  return (
    <div style={{ background: dark ? "#1E293B" : "#E0F2FE", border: "2px solid #0A0A0A", height: 12, width: "100%" }}>
      <div style={{ width: `${pct}%`, height: "100%", background: color, transition: "width 0.6s ease" }} />
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({ label, value, unit, sub, dark, children }: {
  label: string; value?: string | number; unit?: string; sub?: string; dark?: boolean; children?: React.ReactNode;
}) {
  return (
    <div style={{
      background: dark ? "#0F172A" : "#FFFFFF",
      border: "2.5px solid #0A0A0A",
      boxShadow: "4px 4px 0px #0A0A0A",
      padding: "14px",
      display: "flex", flexDirection: "column", gap: 8,
    }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>{label}</p>
      {value !== undefined && (
        <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700, margin: 0, color: dark ? "#F1F5F9" : "#0A0A0A", lineHeight: 1 }}>
          {value}<span style={{ fontSize: 13, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>{unit}</span>
        </p>
      )}
      {sub && <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>{sub}</p>}
      {children}
    </div>
  );
}

// ─── Voice Orb ───────────────────────────────────────────────────────────────
function VoiceOrb({ active, streaming, dark }: { active: boolean; streaming: boolean; dark: boolean }) {
  const bars = Array.from({ length: 11 });
  const orbColor = streaming
    ? "conic-gradient(from 200deg at 40% 38%, #A78BFA, #7C3AED 30%, #6D28D9 55%, #4C1D95 75%, #3B0764)"
    : active
    ? "conic-gradient(from 200deg at 40% 38%, #BAE6FD, #38BDF8 30%, #0EA5E9 55%, #0369A1 75%, #075985)"
    : dark
    ? "conic-gradient(from 200deg at 40% 38%, #1E293B, #334155 50%, #1E293B)"
    : "conic-gradient(from 200deg at 40% 38%, #E2E8F0, #CBD5E1 50%, #94A3B8)";

  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
      <div style={{ position: "relative", width: 180, height: 180, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {(active || streaming) && [0, 1, 2].map((i) => (
          <div key={i} style={{
            position: "absolute", width: 180, height: 180, borderRadius: "50%",
            border: `${1.5 - i * 0.4}px solid rgba(${streaming ? "167,139,250" : "56,189,248"},${0.5 - i * 0.13})`,
            animation: `orb-ring ${1.6 + i * 0.4}s ease-out infinite`,
            animationDelay: `${i * 0.5}s`,
          }} />
        ))}
        <div style={{
          width: 148, height: 148, borderRadius: "50%",
          border: "3px solid #0A0A0A",
          boxShadow: (active || streaming)
            ? `0 0 40px 14px rgba(${streaming ? "167,139,250" : "56,189,248"},0.45), 0 0 80px 30px rgba(${streaming ? "109,40,217" : "14,165,233"},0.25), 4px 4px 0px #0A0A0A`
            : "4px 4px 0px #0A0A0A",
          background: orbColor,
          position: "relative", overflow: "hidden",
          transition: "box-shadow 0.5s, background 0.5s",
          animation: (active || streaming) ? "orb-pulse 2s ease-in-out infinite" : "none",
          display: "flex", alignItems: "center", justifyContent: "center",
        }}>
          <div style={{
            position: "absolute", top: 18, left: 22,
            width: 48, height: 28, borderRadius: "50%",
            background: "rgba(255,255,255,0.35)", filter: "blur(6px)", transform: "rotate(-20deg)",
          }} />
          {(active || streaming) ? (
            <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 44, zIndex: 1 }}>
              {bars.map((_, i) => (
                <div key={i} className="wave-bar" style={{
                  width: 5, height: 8,
                  background: "rgba(255,255,255,0.9)", borderRadius: 3,
                  animationDuration: `${0.35 + i * 0.06}s`,
                  animationDelay: `${i * 0.05}s`,
                }} />
              ))}
            </div>
          ) : (
            <svg width="42" height="42" viewBox="0 0 24 24" fill="none"
              stroke={dark ? "#64748B" : "#94A3B8"} strokeWidth="1.8" strokeLinecap="round" style={{ zIndex: 1 }}>
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </div>
      </div>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, letterSpacing: "0.2em", color: streaming ? "#A78BFA" : active ? "#38BDF8" : "#64748B", margin: 0 }}>
        {streaming ? "● STREAMING TO ASR" : active ? "● CAPTURING AUDIO" : "○ STANDBY"}
      </p>
    </div>
  );
}

// ─── Confidence Meter ─────────────────────────────────────────────────────────
function ConfidenceMeter({ score, label, dark }: { score: number; label: string; dark: boolean }) {
  const pct = Math.round(score * 100);
  const color = LABEL_COLORS[label] ?? "#38BDF8";
  const segments = 20;
  const filled = Math.round((pct / 100) * segments);
  return (
    <div style={{ background: dark ? "#0F172A" : "#fff", border: "2.5px solid #0A0A0A", boxShadow: "4px 4px 0 #0A0A0A", padding: 16, display: "flex", flexDirection: "column", gap: 10 }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Model Confidence</p>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 40, fontWeight: 700, color, lineHeight: 1 }}>{pct}</span>
        <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 14, color: "#64748B" }}>%</span>
        <span style={{
          marginLeft: "auto", fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700,
          padding: "3px 8px", border: "2px solid #0A0A0A", background: color, color: "#fff",
          boxShadow: "2px 2px 0 #0A0A0A", whiteSpace: "nowrap",
        }}>
          {label.toUpperCase().replace(/_/g, " ")}
        </span>
      </div>
      <div style={{ display: "flex", gap: 3 }}>
        {Array.from({ length: segments }, (_, i) => (
          <div key={i} style={{
            flex: 1, height: 18,
            background: i < filled ? color : dark ? "#1E293B" : "#E0F2FE",
            border: "1.5px solid #0A0A0A", transition: "background 0.25s",
          }} />
        ))}
      </div>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>
        RAW_SCORE: {score.toFixed(4)} · MixedNet streaming inference · Vosk ASR
      </p>
    </div>
  );
}

// ─── Latency Spark ────────────────────────────────────────────────────────────
function LatencySpark({ history, dark }: { history: number[]; dark: boolean }) {
  const max = Math.max(...history, 1);
  const min = Math.min(...history, 0);
  const range = max - min || 1;
  const W = 300, H = 44;
  const pts = history.map((v, i) => {
    const x = (i / (history.length - 1)) * W;
    const y = H - ((v - min) / range) * H;
    return `${x},${y}`;
  }).join(" ");
  const last = history[history.length - 1];
  const lx = W, ly = H - ((last - min) / range) * H;
  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke="#38BDF8" strokeWidth="2.5" strokeLinejoin="round" strokeLinecap="round" />
      <circle cx={lx} cy={ly} r="4" fill="#0EA5E9" stroke={dark ? "#0F172A" : "#fff"} strokeWidth="2" />
    </svg>
  );
}

// ─── Data Flow Card ───────────────────────────────────────────────────────────
function DataFlowCard({ rms, peak, dark }: { rms: number; peak: number; dark: boolean }) {
  // Derive KB/s from RMS — RMS ~= audio energy proxy
  const outKBs = parseFloat(((rms / 1000) * 32).toFixed(1));  // PCM bytes per frame
  const inKBs  = parseFloat(((peak / 32768) * 8).toFixed(1)); // control channel

  return (
    <div style={{ background: dark ? "#0F172A" : "#fff", border: "2.5px solid #0A0A0A", boxShadow: "4px 4px 0 #0A0A0A", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Data Flow</p>
      <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>ESP32 → WS → Node.js</p>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 24, fontWeight: 700, margin: 0, color: dark ? "#F1F5F9" : "#0A0A0A" }}>
            {outKBs}<span style={{ fontSize: 12, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>KB/s</span>
          </p>
          <ProgressBar value={outKBs} max={100} warn={60} danger={85} dark={dark} />
        </div>
        <div style={{ width: 1, background: "#0A0A0A", opacity: 0.15 }} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>Node.js → ESP32</p>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 24, fontWeight: 700, margin: 0, color: dark ? "#F1F5F9" : "#0A0A0A" }}>
            {inKBs}<span style={{ fontSize: 12, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>KB/s</span>
          </p>
          <ProgressBar value={inKBs} max={100} warn={60} danger={85} dark={dark} />
        </div>
      </div>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0, borderTop: "1px dashed #CBD5E1", paddingTop: 8 }}>
        INMP441 → I2S → RMS/Peak → MixedNet → WebSocket → Express → Vosk ASR
      </p>
    </div>
  );
}

// ─── Tech Stack Card ──────────────────────────────────────────────────────────
function TechStackCard({ dark, asrOnline }: { dark: boolean; asrOnline: boolean }) {
  const sections = [
    {
      title: "Edge Hardware", color: "#38BDF8",
      rows: [
        ["MCU", "ESP32-S3 (Xtensa LX7 dual-core 240MHz)"],
        ["Mic", "INMP441 (I2S digital MEMS)"],
        ["PSRAM", "8 MB OPI PSRAM"],
        ["Flash", "16 MB SPI Flash"],
        ["SDK", "ESP-IDF + arduino-esp32"],
      ],
    },
    {
      title: "AI / ML", color: "#A855F7",
      rows: [
        ["Architecture", "Streaming MixedNet"],
        ["Inference", "TFLite Micro (INT8)"],
        ["Model Size", "~68 KB"],
        ["Training", "TensorFlow (Python)"],
        ["Quant", "INT8 post-training"],
      ],
    },
    {
      title: "Audio Processing", color: "#22C55E",
      rows: [
        ["Sample Rate", "16 kHz PCM"],
        ["Window", "1500ms / 10ms stride"],
        ["Features", "40-bin MFCC"],
        ["VAD", "RMS threshold always-on"],
        ["Pre-roll", "300ms buffer"],
      ],
    },
    {
      title: "Backend", color: "#F59E0B",
      rows: [
        ["Transport", "WebSocket :8080"],
        ["Backend", "Node.js + Express :5000"],
        ["ASR Engine", `Vosk ${asrOnline ? "✓ LIVE" : "✗ OFFLINE"}`],
        ["Serial", "COM3 @ 115200 baud"],
        ["Dashboard", "React + Vite (TSX)"],
      ],
    },
  ];
  return (
    <div style={{ background: dark ? "#0F172A" : "#fff", border: "2.5px solid #0A0A0A", boxShadow: "4px 4px 0 #0A0A0A", padding: 16, display: "flex", flexDirection: "column", gap: 14 }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Tech Stack</p>
      {sections.map((s) => (
        <div key={s.title}>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700, color: s.color, margin: "0 0 4px 0", letterSpacing: "0.08em" }}>
            ▸ {s.title}
          </p>
          <div style={{ borderLeft: `2px solid ${s.color}`, paddingLeft: 8, display: "flex", flexDirection: "column", gap: 3 }}>
            {s.rows.map(([k, v]) => (
              <div key={k} style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", flexShrink: 0 }}>{k}</span>
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700, textAlign: "right", color: dark ? "#CBD5E1" : "#0A0A0A" }}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [dark, setDark] = useState(false);
  const [uptimeS, setUptimeS] = useState(0);
  const [latHistory, setLatHistory] = useState<number[]>(Array(30).fill(0));
  const [logLines, setLogLines] = useState<string[]>([
    "[BOOT] DORA Monitor ready",
    "[WS]   Connecting to ESP32 bridge ws://localhost:8080",
    "[ASR]  Vosk model check...",
  ]);

  // ── Real live data from ESP32 via WebSocket ──────────────────────────────
  const {
    isConnected,
    micData,
    bridgeState,
    lastKeyword,
    streamingInfo,
    streamingProgress,
    streamingEnd,
    lastTranscript,
    detections,
    asrStatus,
  } = useESP32Bridge();

  const isStreaming = bridgeState === BRIDGE_STATE.STREAMING;
  const isProcessing = bridgeState === BRIDGE_STATE.PROCESSING;
  const isActive = isConnected && micData.rms > 20;

  // Uptime counter — only while connected
  useEffect(() => {
    if (!isConnected) { setUptimeS(0); return; }
    const t = setInterval(() => setUptimeS((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [isConnected]);

  // Latency history from real detections
  useEffect(() => {
    if (lastTranscript.latency > 0) {
      setLatHistory((h) => [...h.slice(1), lastTranscript.latency]);
    }
  }, [lastTranscript.ts]);

  // Live serial log from real events
  useEffect(() => {
    if (!isConnected) {
      setLogLines((l) => [...l, "[WS]   Disconnected — retrying..."]);
      return;
    }
    setLogLines((l) => [...l.slice(-59),
      `[WS]   ESP32 connected — bridge IDLE`,
      `[I2S]  INMP441 mic stream active @ 16kHz`,
      `[ASR]  Vosk ${asrStatus.online ? "LIVE on :2700" : "offline — using mock"}`,
    ]);
  }, [isConnected]);

  useEffect(() => {
    if (micData.rms > 0) {
      setLogLines((l) => [...l.slice(-59),
        `[I2S]  rms=${micData.rms.toFixed(1)} peak=${micData.peak} samples=${micData.samples}`,
      ]);
    }
  }, [micData.samples]); // only log when samples counter changes

  useEffect(() => {
    if (lastKeyword.ts) {
      setLogLines((l) => [...l.slice(-59),
        `[KWS]  Keyword "${lastKeyword.keyword}" detected — conf=${lastKeyword.confidence}`,
        `[STREAM] Pre-roll ${streamingInfo.preRollChunks} chunks → streaming started`,
      ]);
    }
  }, [lastKeyword.ts]);

  useEffect(() => {
    if (lastTranscript.ts) {
      setLogLines((l) => [...l.slice(-59),
        `[ASR]  Transcript: "${lastTranscript.text}" | verdict=${lastTranscript.verdict} lat=${lastTranscript.latency}ms`,
        `[SYS]  Back to IDLE — listening for next keyword`,
      ]);
    }
  }, [lastTranscript.ts]);

  useEffect(() => {
    if (!asrStatus.online) return;
    setLogLines((l) => [...l.slice(-59), `[ASR]  Vosk LIVE on ${asrStatus.url}`]);
  }, [asrStatus.online]);

  const textMain = dark ? "#F1F5F9" : "#0A0A0A";
  const cardBg   = dark ? "#0F172A" : "#FFFFFF";
  const border   = "2.5px solid #0A0A0A";
  const shadow   = "4px 4px 0px #0A0A0A";

  // Confidence from last detection or streaming progress
  const liveConf = lastTranscript.ts
    ? parseFloat(lastTranscript.confidence)
    : isStreaming
    ? parseFloat(lastKeyword.confidence) || 0
    : 0;
  const liveVerdict = lastTranscript.verdict || (isConnected ? "IDLE" : "IDLE");

  return (
    <div className={dark ? "dot-grid-dark" : "dot-grid-light"}
      style={{ minHeight: "100vh", fontFamily: "'DM Sans', sans-serif", color: textMain, padding: "16px" }}>

      {/* ── Header ── */}
      <header style={{
        background: dark ? "#0EA5E9" : "#38BDF8",
        border, boxShadow: shadow,
        padding: "12px 20px",
        display: "flex", flexWrap: "wrap", alignItems: "center", gap: 12,
        marginBottom: 20,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 36, height: 36, border: "2.5px solid #0A0A0A", background: "#fff",
            boxShadow: "2px 2px 0 #0A0A0A", display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "'Space Mono', monospace", fontWeight: 700, fontSize: 14,
          }}>D</div>
          <div>
            <h1 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 900, fontSize: 18, margin: 0, letterSpacing: "-0.02em", lineHeight: 1 }}>
              DORA MONITOR
            </h1>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, margin: 0, opacity: 0.7 }}>
              ESP32-S3 · MixedNet · WebSocket · Vosk ASR
            </p>
          </div>
        </div>

        {/* Status badges */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{
            fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700,
            border, background: isConnected ? "#22C55E" : "#EF4444", color: "#fff",
            padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A",
          }}>
            {isConnected ? "● CONNECTED" : "○ OFFLINE"}
          </span>

          {isConnected && (
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, border, background: "#A855F7", color: "#fff", padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A" }}>
              ● REC
            </span>
          )}

          <span style={{
            fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700,
            border, background: asrStatus.online ? "#0EA5E9" : "#64748B", color: "#fff",
            padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A",
          }}>
            ASR: {asrStatus.online ? "VOSK LIVE" : "MOCK"}
          </span>

          {isConnected && (
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12 }}>
              ⏱ {fmtUptime(uptimeS)}
            </span>
          )}

          {isStreaming && (
            <span style={{
              fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700,
              border, background: "#7C3AED", color: "#fff",
              padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A",
              animation: "tick 1s infinite",
            }}>
              ▶ STREAMING {streamingProgress.elapsedMs}ms
            </span>
          )}

          {isProcessing && (
            <span style={{
              fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700,
              border, background: "#F59E0B", color: "#fff",
              padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A",
            }}>
              ⏳ ASR PROCESSING
            </span>
          )}
        </div>

        {/* Right: clock + dark toggle */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <LiveClock dark={dark} />
          <button onClick={() => setDark(!dark)} style={{
            fontFamily: "'Space Mono', monospace", fontSize: 12, fontWeight: 700,
            border, boxShadow: "3px 3px 0 #0A0A0A",
            background: dark ? "#1E293B" : "#fff", color: dark ? "#F1F5F9" : "#0A0A0A",
            padding: "6px 14px", cursor: "pointer",
          }}>
            {dark ? "☀ LIGHT" : "☾ DARK"}
          </button>
        </div>
      </header>

      {/* ── Not connected banner ── */}
      {!isConnected && (
        <div style={{
          background: "#EF4444", border, boxShadow: shadow,
          padding: "12px 20px", marginBottom: 16,
          fontFamily: "'Space Mono', monospace", fontSize: 12, fontWeight: 700, color: "#fff",
          display: "flex", alignItems: "center", gap: 12,
        }}>
          ⚠ ESP32 NOT CONNECTED — Start serial bridge: <code style={{ background: "rgba(0,0,0,0.3)", padding: "2px 8px" }}>node esp32-serial-bridge.js</code>
          then check <code style={{ background: "rgba(0,0,0,0.3)", padding: "2px 8px" }}>http://localhost:3000/health</code>
        </div>
      )}

      {/* ── Streaming state banner ── */}
      {isConnected && (isStreaming || isProcessing) && (
        <div style={{
          background: isStreaming ? "rgba(124,58,237,0.12)" : "rgba(245,158,11,0.12)",
          border: `2.5px solid ${isStreaming ? "#7C3AED" : "#F59E0B"}`,
          boxShadow: shadow, padding: "12px 20px", marginBottom: 16,
          display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap",
        }}>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 13, fontWeight: 700, color: isStreaming ? "#7C3AED" : "#F59E0B" }}>
            {isStreaming ? `▶ STREAMING TO ASR — keyword "${streamingInfo.keyword}" detected` : "⏳ PROCESSING — waiting for ASR transcript"}
          </span>
          {isStreaming && (
            <>
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#64748B" }}>
                elapsed: {streamingProgress.elapsedMs}ms · chunks: {streamingProgress.chunksCollected} · rms: {streamingProgress.rms.toFixed(1)}
              </span>
              {/* Silence gate */}
              <div style={{ display: "flex", alignItems: "center", gap: 8, flex: 1, minWidth: 200 }}>
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", whiteSpace: "nowrap" }}>VAD silence gate</span>
                <div style={{ flex: 1, height: 8, background: "#1E293B", border: "1px solid #444", borderRadius: 4 }}>
                  <div style={{
                    height: "100%",
                    width: `${Math.min(100, (streamingProgress.silenceCount / streamingProgress.silenceFramesNeeded) * 100)}%`,
                    background: streamingProgress.silenceCount > 10 ? "#EF4444" : "#22C55E",
                    borderRadius: 4, transition: "width 0.2s ease",
                  }} />
                </div>
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", whiteSpace: "nowrap" }}>
                  {streamingProgress.silenceCount}/{streamingProgress.silenceFramesNeeded}
                </span>
              </div>
            </>
          )}
        </div>
      )}

      {/* ── Last transcript banner ── */}
      {isConnected && lastTranscript.ts && (
        <div style={{
          background: lastTranscript.verdict === "TP" ? "rgba(34,197,94,0.08)" : "rgba(239,68,68,0.08)",
          border: `2.5px solid ${lastTranscript.verdict === "TP" ? "#22C55E" : "#EF4444"}`,
          boxShadow: shadow, padding: "12px 20px", marginBottom: 16,
          display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap",
        }}>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#64748B" }}>LAST TRANSCRIPT</span>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 16, fontWeight: 700, color: textMain }}>
            {lastTranscript.text || "(no command)"}
          </span>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, padding: "3px 8px", border, background: LABEL_COLORS[lastTranscript.verdict] ?? "#64748B", color: "#fff", boxShadow: "2px 2px 0 #0A0A0A" }}>
            {lastTranscript.verdict}
          </span>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#64748B" }}>conf: {lastTranscript.confidence}</span>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#64748B" }}>latency: {lastTranscript.latency}ms</span>
          <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, color: "#64748B" }}>duration: {lastTranscript.durationMs}ms</span>
        </div>
      )}

      {/* ── Main Grid ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(12, 1fr)", gap: 16 }}>

        {/* LEFT COLUMN */}
        <div style={{ gridColumn: "span 3", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Orb panel */}
          <div style={{ background: cardBg, border, boxShadow: shadow, padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <VoiceOrb active={isActive} streaming={isStreaming} dark={dark} />
            {isConnected && (
              <div style={{ width: "100%", background: "#38BDF8", border, boxShadow: "2px 2px 0 #0A0A0A", padding: "8px 12px", textAlign: "center" }}>
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, margin: 0 }}>
                  🎙 RMS: {micData.rms.toFixed(1)} · Peak: {micData.peak}
                </p>
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, margin: "2px 0 0", opacity: 0.7 }}>
                  Samples: {micData.samples.toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {/* Tech Stack */}
          <TechStackCard dark={dark} asrOnline={asrStatus.online} />
        </div>

        {/* RIGHT 9 COLUMNS */}
        <div style={{ gridColumn: "span 9", display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Row 1: Hardware stats — CPU, RAM, Heap, Temp, Inference */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            <StatCard
              label="CPU Utilization"
              value={isConnected && (micData as any).cpuUtil !== undefined ? (micData as any).cpuUtil.toFixed(1) : (isConnected ? "0.0" : "--")}
              unit="%"
              sub={`PS Target <10% · ${isConnected ? micData.cpuMhz : 240} MHz`}
              dark={dark}
            >
              {isConnected && <ProgressBar value={(micData as any).cpuUtil || 0} max={100} warn={10} danger={25} dark={dark} />}
            </StatCard>
            <StatCard
              label="RAM Used"
              value={isConnected ? ((512 - micData.heapFreeKB)).toFixed(0) : "--"}
              unit="KB"
              sub={`/ 512 KB · ${isConnected ? Math.round((512 - micData.heapFreeKB) / 512 * 100) : "--"}% used`}
              dark={dark}
            >
              {isConnected && <ProgressBar value={512 - micData.heapFreeKB} max={512} warn={60} danger={85} dark={dark} />}
            </StatCard>
            <StatCard
              label="Heap Free"
              value={isConnected ? micData.heapFreeKB.toFixed(0) : "--"}
              unit="KB"
              sub="Internal SRAM heap"
              dark={dark}
            >
              {isConnected && <ProgressBar value={micData.heapFreeKB} max={512} warn={60} danger={30} dark={dark} />}
            </StatCard>
            <StatCard
              label="Core Temp"
              value={isConnected ? micData.coreTemp.toFixed(1) : "--"}
              unit="°C"
              sub="Internal die sensor"
              dark={dark}
            />
          </div>

          {/* Row 1b: Inference timing + PSRAM + mic signal */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            <StatCard
              label="Inference Time"
              value={isConnected && micData.inferUs > 0 ? (micData.inferUs / 1000).toFixed(1) : "--"}
              unit="ms"
              sub="TFLite Invoke() per frame"
              dark={dark}
            >
              {isConnected && micData.inferUs > 0 && <ProgressBar value={micData.inferUs / 1000} max={20} warn={10} danger={15} dark={dark} />}
            </StatCard>
            <StatCard
              label="Feature Extract"
              value={isConnected && micData.featUs > 0 ? (micData.featUs / 1000).toFixed(1) : "--"}
              unit="ms"
              sub="PCAN mel filterbank"
              dark={dark}
            />
            <StatCard
              label="PSRAM Free"
              value={isConnected ? micData.psramFreeKB.toFixed(0) : "--"}
              unit="KB"
              sub="8 MB OPI PSRAM"
              dark={dark}
            >
              {isConnected && <ProgressBar value={micData.psramFreeKB} max={8192} warn={40} danger={20} dark={dark} />}
            </StatCard>
            <StatCard
              label="KWS Score"
              value={isConnected ? micData.smoothed.toFixed(3) : "--"}
              unit=""
              sub={`raw: ${isConnected ? micData.confidence.toFixed(3) : "--"} · thresh: 0.75`}
              dark={dark}
            >
              {isConnected && <ProgressBar value={micData.smoothed * 100} max={100} warn={60} danger={75} dark={dark} />}
            </StatCard>
          </div>

          {/* Row 2: RMS + Peak + Bridge State + Detections */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            <StatCard label="RMS Level" value={isConnected ? micData.rms.toFixed(1) : "--"} unit="" sub="I2S audio energy" dark={dark}>
              {isConnected && <ProgressBar value={micData.rms} max={500} warn={200} danger={400} dark={dark} />}
            </StatCard>
            <StatCard label="Peak Amplitude" value={isConnected ? micData.peak : "--"} unit="" sub="Max sample value" dark={dark}>
              {isConnected && <ProgressBar value={micData.peak} max={32768} warn={70} danger={88} dark={dark} />}
            </StatCard>
            <StatCard label="Bridge State" value={bridgeState} unit="" sub="Pipeline state machine" dark={dark}>
              {isConnected && (
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: bridgeState === BRIDGE_STATE.STREAMING ? "#7C3AED" : bridgeState === BRIDGE_STATE.PROCESSING ? "#F59E0B" : "#22C55E", margin: 0 }}>
                  {bridgeState === BRIDGE_STATE.IDLE ? "✓ LISTENING" : bridgeState === BRIDGE_STATE.STREAMING ? "▶ STREAMING" : "⏳ PROCESSING"}
                </p>
              )}
            </StatCard>
            <StatCard label="Detections" value={detections.length} unit="" sub={`Last: ${detections[0]?.time ?? "none"}`} dark={dark}>
              {detections.length > 0 && (
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: LABEL_COLORS[detections[0].verdict] ?? "#64748B", margin: 0 }}>
                  {detections[0].verdict} · {detections[0].confidence}
                </p>
              )}
            </StatCard>
          </div>

          {/* Row 2: Latency + ASR stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            {/* Latency spans 2 */}
            <div style={{ gridColumn: "span 2", background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>ASR Latency</p>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 30, fontWeight: 700, color: textMain }}>
                  {lastTranscript.latency > 0 ? lastTranscript.latency : "--"}
                </span>
                <span style={{ color: "#64748B", fontSize: 13 }}>ms</span>
                <span style={{ marginLeft: "auto", fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B" }}>last 30 detections</span>
              </div>
              <div style={{ border: "2px solid #0A0A0A", background: dark ? "#020B14" : "#F0F9FF", padding: 4, boxShadow: "2px 2px 0 #0A0A0A" }}>
                <LatencySpark history={latHistory} dark={dark} />
              </div>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>
                keyword detected → ASR transcript returned
              </p>
            </div>

            {/* Pre-roll info */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Pre-Roll Buffer</p>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700, margin: 0, color: textMain, lineHeight: 1 }}>
                {isStreaming ? streamingInfo.preRollChunks : "--"}
                <span style={{ fontSize: 13, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>chunks</span>
              </p>
              {isStreaming && (
                <>
                  <ProgressBar value={streamingInfo.preRollChunks} max={6} warn={3} danger={5} dark={dark} />
                  <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>300ms audio before keyword</p>
                </>
              )}
              {!isStreaming && <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>Filled on keyword detect</p>}
            </div>

            {/* Stream duration */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Last Stream</p>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700, margin: 0, color: textMain, lineHeight: 1 }}>
                {streamingEnd.durationMs > 0 ? streamingEnd.durationMs : "--"}
                <span style={{ fontSize: 13, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>ms</span>
              </p>
              {streamingEnd.durationMs > 0 && (
                <>
                  <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#22C55E", margin: 0 }}>
                    ended: {streamingEnd.reason}
                  </p>
                  <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>
                    {streamingEnd.chunks} chunks captured
                  </p>
                </>
              )}
            </div>
          </div>

          {/* Row 3: Data Flow + Stream Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <DataFlowCard rms={isConnected ? micData.rms : 0} peak={isConnected ? micData.peak : 0} dark={dark} />

            {/* Stream stats */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Stream Stats</p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  ["TOTAL DETECTIONS",  `${detections.length}`],
                  ["TP COUNT",          `${detections.filter(d => d.verdict === "TP" || d.verdict === "TP_KWS_ONLY").length}`],
                  ["FP COUNT",          `${detections.filter(d => d.verdict === "FP").length}`],
                  ["LAST KEYWORD",      lastKeyword.keyword || "--"],
                  ["LAST CONF",         lastKeyword.confidence || "--"],
                  ["ASR SOURCE",        asrStatus.online ? "Vosk :2700" : "Mock"],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: "#64748B", margin: 0 }}>{k}</p>
                    <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 16, fontWeight: 700, margin: 0, color: textMain }}>{v}</p>
                  </div>
                ))}
              </div>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0, borderTop: "1px dashed #CBD5E1", paddingTop: 8 }}>
                TRANSPORT: WebSocket :8080 · ASR: {asrStatus.online ? `Vosk ${asrStatus.url}` : "mock"}
              </p>
            </div>
          </div>

          {/* Row 4: Confidence + Detection Log */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <ConfidenceMeter score={liveConf} label={liveVerdict} dark={dark} />

            {/* Live detection log */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Detection Log</p>
                {isConnected && (
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700, background: "#22C55E", color: "#fff", padding: "2px 8px", border: "1.5px solid #0A0A0A", boxShadow: "1px 1px 0 #0A0A0A" }}>
                    LIVE
                  </span>
                )}
              </div>
              {detections.length === 0 ? (
                <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "#64748B", fontFamily: "'Space Mono', monospace", fontSize: 11 }}>
                  Say "DORA" to trigger detection
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: 4, maxHeight: 220, overflowY: "auto" }}>
                  {detections.map((d) => (
                    <div key={d.id} style={{
                      background: dark ? "#0A0A1A" : "#F0F9FF", border: "1.5px solid #0A0A0A",
                      padding: "6px 10px", display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap",
                    }}>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B" }}>{d.time}</span>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, color: textMain, flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                        {d.transcript || d.keyword || "DORA"}
                      </span>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B" }}>{d.confidence}</span>
                      <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700, padding: "1px 6px", border: "1.5px solid #0A0A0A", background: LABEL_COLORS[d.verdict] ?? "#64748B", color: "#fff" }}>
                        {d.verdict}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Row 5: Serial Log */}
          <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Serial Log</p>
              {isConnected && (
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700, background: "#22C55E", color: "#fff", padding: "2px 8px", border: "1.5px solid #0A0A0A", boxShadow: "1px 1px 0 #0A0A0A" }}>
                  LIVE
                </span>
              )}
            </div>
            <div style={{
              background: "#020B14", border: "2px solid #0A0A0A", padding: 10,
              fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#38BDF8",
              overflowY: "auto", maxHeight: 160,
              display: "flex", flexDirection: "column", gap: 2,
              boxShadow: "2px 2px 0 #0A0A0A",
            }}>
              {logLines.map((l, i) => (
                <p key={i} style={{ margin: 0, color: i === logLines.length - 1 ? "#FFFFFF" : "#38BDF8", opacity: i === logLines.length - 1 ? 1 : 0.75 }}>
                  {l}
                </p>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* ── Footer ── */}
      <footer style={{
        marginTop: 20, background: "#0A0A0A", border, boxShadow: shadow,
        padding: "8px 20px", display: "flex", flexWrap: "wrap", gap: 16, alignItems: "center",
        fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#38BDF8",
      }}>
        <span>DORA MONITOR v4.1</span>
        <span style={{ opacity: 0.3 }}>·</span>
        <span style={{ color: "#64748B" }}>ESP32-S3 · MixedNet · WebSocket · Vosk ASR · React+Vite</span>
        <span style={{ marginLeft: "auto", opacity: 0.5 }}>
          {isConnected ? `LIVE · ${bridgeState}` : "IDLE — waiting for ESP32"}
        </span>
      </footer>
    </div>
  );
}
