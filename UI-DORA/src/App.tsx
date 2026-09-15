import { useState, useEffect, useRef } from "react";

// ─── Types ────────────────────────────────────────────────────────────────────
interface ESP32Stats {
  ramUsed: number;
  ramTotal: number;
  cpuUsage: number;
  flashUsed: number;
  flashTotal: number;
  tempC: number;
  uptimeS: number;
  wifiRssi: number;
  dataFlowIn: number;
  dataFlowOut: number;
  cloudSentMB: number;
  audioSentSec: number;
  latencyMs: number;
  confidence: number;
  detectedLabel: string;
  packetLoss: number;
  heapFree: number;
  psramFree: number;
  i2sBufferFill: number;
  fftFrames: number;
  wsReconnects: number;
}

const INITIAL_STATS: ESP32Stats = {
  ramUsed: 180, ramTotal: 512,
  cpuUsage: 42,
  flashUsed: 1.8, flashTotal: 16,
  tempC: 38,
  uptimeS: 0,
  wifiRssi: -62,
  dataFlowIn: 12.4,
  dataFlowOut: 28.7,
  cloudSentMB: 0,
  audioSentSec: 0,
  latencyMs: 112,
  confidence: 0.87,
  detectedLabel: "speech",
  packetLoss: 0.3,
  heapFree: 220,
  psramFree: 6800,
  i2sBufferFill: 55,
  fftFrames: 0,
  wsReconnects: 0,
};

const LABELS = ["speech", "background_noise", "wake_word", "keyword_hey_dora", "silence"];
const LABEL_COLORS: Record<string, string> = {
  speech: "#22C55E",
  background_noise: "#F59E0B",
  wake_word: "#38BDF8",
  keyword_hey_dora: "#A855F7",
  silence: "#64748B",
};

function jitter(val: number, range: number, min: number, max: number) {
  return Math.min(max, Math.max(min, val + (Math.random() - 0.5) * range));
}

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
function ProgressBar({ value, max, warn = 70, danger = 90, dark }: { value: number; max: number; warn?: number; danger?: number; dark?: boolean }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct >= danger ? "#EF4444" : pct >= warn ? "#F59E0B" : "#38BDF8";
  return (
    <div
      style={{
        background: dark ? "#1E293B" : "#E0F2FE",
        border: "2px solid #0A0A0A",
        height: 12,
        width: "100%",
      }}
    >
      <div style={{ width: `${pct}%`, height: "100%", background: color, transition: "width 0.6s ease" }} />
    </div>
  );
}

// ─── Stat Card ────────────────────────────────────────────────────────────────
function StatCard({
  label, value, unit, sub, dark, children,
}: {
  label: string; value?: string | number; unit?: string; sub?: string; dark?: boolean; children?: React.ReactNode;
}) {
  return (
    <div
      style={{
        background: dark ? "#0F172A" : "#FFFFFF",
        border: "2.5px solid #0A0A0A",
        boxShadow: "4px 4px 0px #0A0A0A",
        padding: "14px",
        display: "flex",
        flexDirection: "column",
        gap: 8,
      }}
    >
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

// ─── Orb ─────────────────────────────────────────────────────────────────────
function VoiceOrb({ active, dark }: { active: boolean; dark: boolean }) {
  const bars = Array.from({ length: 11 });
  return (
    <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
      {/* Orb container */}
      <div style={{ position: "relative", width: 180, height: 180, display: "flex", alignItems: "center", justifyContent: "center" }}>
        {/* Outer glow rings */}
        {active && (
          <>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  position: "absolute",
                  width: 180, height: 180,
                  borderRadius: "50%",
                  border: `${1.5 - i * 0.4}px solid rgba(56,189,248,${0.5 - i * 0.13})`,
                  animation: `orb-ring ${1.6 + i * 0.4}s ease-out infinite`,
                  animationDelay: `${i * 0.5}s`,
                }}
              />
            ))}
          </>
        )}

        {/* Main sphere */}
        <div
          style={{
            width: 148,
            height: 148,
            borderRadius: "50%",
            border: "3px solid #0A0A0A",
            boxShadow: active
              ? `0 0 0 0 rgba(56,189,248,0), 0 0 40px 14px rgba(56,189,248,0.45), 0 0 80px 30px rgba(14,165,233,0.25), 4px 4px 0px #0A0A0A`
              : `4px 4px 0px #0A0A0A`,
            background: active
              ? "conic-gradient(from 200deg at 40% 38%, #BAE6FD, #38BDF8 30%, #0EA5E9 55%, #0369A1 75%, #075985)"
              : dark
              ? "conic-gradient(from 200deg at 40% 38%, #1E293B, #334155 50%, #1E293B)"
              : "conic-gradient(from 200deg at 40% 38%, #E2E8F0, #CBD5E1 50%, #94A3B8)",
            position: "relative",
            overflow: "hidden",
            transition: "box-shadow 0.5s, background 0.5s",
            animation: active ? "orb-pulse 2s ease-in-out infinite" : "none",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          {/* Specular highlight */}
          <div
            style={{
              position: "absolute",
              top: 18, left: 22,
              width: 48, height: 28,
              borderRadius: "50%",
              background: "rgba(255,255,255,0.35)",
              filter: "blur(6px)",
              transform: "rotate(-20deg)",
            }}
          />
          {/* Inner content */}
          {active ? (
            <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 44, zIndex: 1 }}>
              {bars.map((_, i) => (
                <div
                  key={i}
                  className="wave-bar"
                  style={{
                    width: 5,
                    height: 8,
                    background: "rgba(255,255,255,0.9)",
                    borderRadius: 3,
                    animationDuration: `${0.35 + i * 0.06}s`,
                    animationDelay: `${i * 0.05}s`,
                  }}
                />
              ))}
            </div>
          ) : (
            <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke={dark ? "#64748B" : "#94A3B8"} strokeWidth="1.8" strokeLinecap="round" style={{ zIndex: 1 }}>
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          )}
        </div>
      </div>

      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, letterSpacing: "0.2em", color: active ? "#38BDF8" : "#64748B", margin: 0 }}>
        {active ? "● CAPTURING AUDIO" : "○ STANDBY"}
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
        <span
          style={{
            marginLeft: "auto",
            fontFamily: "'Space Mono', monospace",
            fontSize: 10,
            fontWeight: 700,
            padding: "3px 8px",
            border: "2px solid #0A0A0A",
            background: color,
            color: "#fff",
            boxShadow: "2px 2px 0 #0A0A0A",
            whiteSpace: "nowrap",
          }}
        >
          {label.toUpperCase().replace(/_/g, " ")}
        </span>
      </div>
      <div style={{ display: "flex", gap: 3 }}>
        {Array.from({ length: segments }, (_, i) => (
          <div
            key={i}
            style={{
              flex: 1,
              height: 18,
              background: i < filled ? color : dark ? "#1E293B" : "#E0F2FE",
              border: "1.5px solid #0A0A0A",
              transition: "background 0.25s",
            }}
          />
        ))}
      </div>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>
        RAW_SCORE: {score.toFixed(4)} · MixedNet streaming inference
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
function DataFlowCard({ inKBs, outKBs, dark }: { inKBs: number; outKBs: number; dark: boolean }) {
  return (
    <div style={{ background: dark ? "#0F172A" : "#fff", border: "2.5px solid #0A0A0A", boxShadow: "4px 4px 0 #0A0A0A", padding: 16, display: "flex", flexDirection: "column", gap: 12 }}>
      <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Data Flow</p>
      <div style={{ display: "flex", gap: 16, alignItems: "stretch" }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>ESP32 → WS → Node.js</p>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 24, fontWeight: 700, margin: 0, color: dark ? "#F1F5F9" : "#0A0A0A" }}>
            {outKBs.toFixed(1)}<span style={{ fontSize: 12, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>KB/s</span>
          </p>
          <ProgressBar value={outKBs} max={100} warn={60} danger={85} dark={dark} />
        </div>
        <div style={{ width: 1, background: "#0A0A0A", opacity: 0.15 }} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 6 }}>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>Node.js → ESP32</p>
          <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 24, fontWeight: 700, margin: 0, color: dark ? "#F1F5F9" : "#0A0A0A" }}>
            {inKBs.toFixed(1)}<span style={{ fontSize: 12, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>KB/s</span>
          </p>
          <ProgressBar value={inKBs} max={100} warn={60} danger={85} dark={dark} />
        </div>
      </div>
      <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0, borderTop: "1px dashed #CBD5E1", paddingTop: 8 }}>
        INMP441 → I2S → FFT+MEL → MixedNet → WebSocket → Express → Vosk ASR
      </p>
    </div>
  );
}

// ─── Tech Stack Card (replaces old Model Details) ─────────────────────────────
function TechStackCard({ dark }: { dark: boolean }) {
  const sections = [
    {
      title: "Edge Hardware",
      color: "#38BDF8",
      rows: [
        ["MCU", "ESP32-S3 (Xtensa LX7 dual-core 240MHz)"],
        ["Mic", "INMP441 (I2S digital MEMS)"],
        ["PSRAM", "8 MB OPI PSRAM"],
        ["Flash", "16 MB SPI Flash"],
        ["SDK", "ESP-IDF v5.1 + arduino-esp32"],
      ],
    },
    {
      title: "AI / ML",
      color: "#A855F7",
      rows: [
        ["Training", "TensorFlow (Python)"],
        ["Architecture", "Streaming MixedNet"],
        ["Inference", "Custom C++ on-device"],
        ["Quant", "INT8 post-training"],
        ["Model Size", "~98 KB"],
      ],
    },
    {
      title: "Audio Processing",
      color: "#22C55E",
      rows: [
        ["Sample Rate", "16 kHz PCM"],
        ["Training", "Librosa (Python)"],
        ["On-device", "FFT + Mel Filterbank"],
        ["Window", "1000ms / 250ms hop"],
        ["Features", "40-dim MFCCs"],
      ],
    },
    {
      title: "Protocol & Backend",
      color: "#F59E0B",
      rows: [
        ["Transport", "WebSocket (plain, real-time)"],
        ["Backend", "Node.js + Express"],
        ["ASR Engine", "Vosk ASR"],
        ["Dashboard", "React + Vite"],
        ["Output Classes", "5 labels"],
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
  const [powered, setPowered] = useState(false);
  const [stats, setStats] = useState<ESP32Stats>(INITIAL_STATS);
  const [latHistory, setLatHistory] = useState<number[]>(Array(30).fill(112));
  const [logLines, setLogLines] = useState<string[]>([
    "[BOOT] System ready — waiting for ESP32-S3",
    "[WS]   WebSocket server listening :3001",
    "[ASR]  Vosk model loaded en-us-0.22",
  ]);
  const statsRef = useRef(stats);
  statsRef.current = stats;
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!powered) {
      if (intervalRef.current) clearInterval(intervalRef.current);
      return;
    }
    intervalRef.current = setInterval(() => {
      setStats((prev) => {
        const cpu = jitter(prev.cpuUsage, 14, 18, 97);
        const ram = jitter(prev.ramUsed, 18, 130, 490);
        const lat = jitter(prev.latencyMs, 28, 38, 310);
        const conf = jitter(prev.confidence, 0.07, 0.42, 0.99);
        const labelIdx = conf > 0.85 ? 3 : conf > 0.70 ? 2 : conf > 0.55 ? 0 : Math.floor(Math.random() * LABELS.length);
        return {
          ...prev,
          cpuUsage: cpu,
          ramUsed: ram,
          flashUsed: jitter(prev.flashUsed, 0.005, 1.6, 14),
          tempC: jitter(prev.tempC, 1.2, 30, 72),
          uptimeS: prev.uptimeS + 1,
          wifiRssi: jitter(prev.wifiRssi, 2, -82, -38),
          dataFlowIn: jitter(prev.dataFlowIn, 4, 2, 75),
          dataFlowOut: jitter(prev.dataFlowOut, 7, 8, 90),
          cloudSentMB: prev.cloudSentMB + 0.004,
          audioSentSec: prev.audioSentSec + 1,
          latencyMs: lat,
          confidence: conf,
          detectedLabel: LABELS[labelIdx],
          packetLoss: jitter(prev.packetLoss, 0.15, 0, 3.5),
          heapFree: jitter(prev.heapFree, 12, 80, 300),
          psramFree: jitter(prev.psramFree, 80, 5000, 7900),
          i2sBufferFill: jitter(prev.i2sBufferFill, 8, 20, 95),
          fftFrames: prev.fftFrames + Math.floor(Math.random() * 4 + 2),
          wsReconnects: Math.random() < 0.005 ? prev.wsReconnects + 1 : prev.wsReconnects,
        };
      });
      setLatHistory((h) => [...h.slice(1), statsRef.current.latencyMs]);
      if (Math.random() < 0.35) {
        const s = statsRef.current;
        const msgs = [
          `[INFER] label=${s.detectedLabel} conf=${s.confidence.toFixed(3)} lat=${s.latencyMs.toFixed(0)}ms`,
          `[WS]   PCM chunk 512B → Node.js`,
          `[ASR]  Vosk transcript: "${["hey dora", "start", "stop recording", "what is the time"][Math.floor(Math.random() * 4)]}"`,
          `[MEL]  FFT frame #${s.fftFrames} processed`,
          `[MEM]  heap_free=${s.heapFree.toFixed(0)}KB psram_free=${(s.psramFree / 1024).toFixed(1)}MB`,
          `[I2S]  buf=${s.i2sBufferFill.toFixed(0)}% temp=${s.tempC.toFixed(1)}°C`,
          `[NET]  RTT=${s.latencyMs.toFixed(0)}ms rssi=${s.wifiRssi}dBm`,
        ];
        setLogLines((l) => [...l.slice(-59), msgs[Math.floor(Math.random() * msgs.length)]]);
      }
    }, 1000);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [powered]);

  function handlePower() {
    const next = !powered;
    setPowered(next);
    if (!next) {
      setLogLines((l) => [...l, "[SYS]  ESP32-S3 disconnected", "[WS]   Client connection closed"]);
    } else {
      setStats((s) => ({ ...s, uptimeS: 0, cloudSentMB: 0, audioSentSec: 0, fftFrames: 0, wsReconnects: 0 }));
      setLogLines((l) => [...l,
        "[BOOT] ESP32-S3 connected via WebSocket",
        "[SYS]  Handshake complete — starting audio stream",
        "[I2S]  INMP441 mic initialised @ 16kHz",
        "[MEL]  FFT + Mel Filterbank active",
      ]);
      setTimeout(() => setLogLines((l) => [...l,
        "[MODEL] MixedNet streaming inference active",
        "[ASR]  Vosk ASR ready",
        "[REC]  Continuous audio capture STARTED",
      ]), 1500);
    }
  }

  const cardBg = dark ? "#0F172A" : "#FFFFFF";
  const border = "2.5px solid #0A0A0A";
  const shadow = "4px 4px 0px #0A0A0A";
  const textMain = dark ? "#F1F5F9" : "#0A0A0A";

  return (
    <div
      className={dark ? "dot-grid-dark" : "dot-grid-light"}
      style={{
        minHeight: "100vh",
        fontFamily: "'DM Sans', sans-serif",
        color: textMain,
        padding: "16px",
      }}
    >
      {/* ── Header ── */}
      <header
        style={{
          background: dark ? "#0EA5E9" : "#38BDF8",
          border,
          boxShadow: shadow,
          padding: "12px 20px",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          gap: 12,
          marginBottom: 20,
        }}
      >
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 36, height: 36,
              border: "2.5px solid #0A0A0A",
              background: "#fff",
              boxShadow: "2px 2px 0 #0A0A0A",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontFamily: "'Space Mono', monospace", fontWeight: 700, fontSize: 14,
            }}
          >D</div>
          <div>
            <h1 style={{ fontFamily: "'DM Sans', sans-serif", fontWeight: 900, fontSize: 18, margin: 0, letterSpacing: "-0.02em", lineHeight: 1 }}>
              DORA MONITOR
            </h1>
            <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, margin: 0, opacity: 0.7 }}>
              ESP32-S3 · MixedNet · WebSocket · Vosk ASR
            </p>
          </div>
        </div>

        {/* Center status */}
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <span
            style={{
              fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700,
              border, background: powered ? "#22C55E" : "#EF4444", color: "#fff",
              padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A",
            }}
          >
            {powered ? "● CONNECTED" : "○ OFFLINE"}
          </span>
          {powered && (
            <>
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, border, background: "#A855F7", color: "#fff", padding: "4px 10px", boxShadow: "2px 2px 0 #0A0A0A" }}>
                ● REC
              </span>
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 12 }}>
                ⏱ {fmtUptime(stats.uptimeS)}
              </span>
            </>
          )}
        </div>

        {/* Right: clock + controls */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <LiveClock dark={dark} />

          {/* Dark mode toggle */}
          <button
            onClick={() => setDark(!dark)}
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 12, fontWeight: 700,
              border, boxShadow: "3px 3px 0 #0A0A0A",
              background: dark ? "#1E293B" : "#fff",
              color: dark ? "#F1F5F9" : "#0A0A0A",
              padding: "6px 14px",
              cursor: "pointer",
            }}
          >
            {dark ? "☀ LIGHT" : "☾ DARK"}
          </button>

          {/* Power button */}
          <button
            onClick={handlePower}
            style={{
              fontFamily: "'Space Mono', monospace",
              fontSize: 12, fontWeight: 700,
              border, boxShadow: "3px 3px 0 #0A0A0A",
              background: powered ? "#EF4444" : "#22C55E",
              color: "#fff",
              padding: "6px 14px",
              cursor: "pointer",
            }}
          >
            {powered ? "⏻ DISCONNECT" : "⏻ CONNECT ESP32"}
          </button>
        </div>
      </header>

      {/* ── Main Grid ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(12, 1fr)", gap: 16 }}>

        {/* LEFT COLUMN */}
        <div style={{ gridColumn: "span 3", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Orb panel */}
          <div style={{ background: cardBg, border, boxShadow: shadow, padding: 24, display: "flex", flexDirection: "column", alignItems: "center", gap: 16 }}>
            <VoiceOrb active={powered} dark={dark} />
            {powered && (
              <div style={{ width: "100%", background: "#38BDF8", border, boxShadow: "2px 2px 0 #0A0A0A", padding: "8px 12px", textAlign: "center" }}>
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 11, fontWeight: 700, margin: 0 }}>
                  🎙 {stats.audioSentSec}s · {stats.cloudSentMB.toFixed(2)} MB
                </p>
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, margin: "2px 0 0", opacity: 0.7 }}>
                  FFT frames: {stats.fftFrames.toLocaleString()}
                </p>
              </div>
            )}
          </div>

          {/* Tech Stack */}
          <TechStackCard dark={dark} />
        </div>

        {/* RIGHT 9 COLUMNS */}
        <div style={{ gridColumn: "span 9", display: "flex", flexDirection: "column", gap: 16 }}>

          {/* Row 1: 4 stat cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            <StatCard label="CPU Usage" value={powered ? stats.cpuUsage.toFixed(0) : "--"} unit="%" sub="LX7 dual-core 240MHz" dark={dark}>
              {powered && <ProgressBar value={stats.cpuUsage} max={100} warn={70} danger={90} dark={dark} />}
            </StatCard>
            <StatCard label="RAM Used" value={powered ? stats.ramUsed.toFixed(0) : "--"} unit="MB" sub={`/ 512 MB  •  ${Math.round((stats.ramUsed / 512) * 100)}% used`} dark={dark}>
              {powered && <ProgressBar value={stats.ramUsed} max={512} warn={70} danger={88} dark={dark} />}
            </StatCard>
            <StatCard label="Heap Free" value={powered ? stats.heapFree.toFixed(0) : "--"} unit="KB" sub="Internal SRAM heap" dark={dark}>
              {powered && (
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: stats.heapFree < 100 ? "#EF4444" : "#22C55E", margin: 0 }}>
                  {stats.heapFree < 100 ? "⚠ LOW" : "✓ OK"}
                </p>
              )}
            </StatCard>
            <StatCard label="Core Temp" value={powered ? stats.tempC.toFixed(1) : "--"} unit="°C" sub="Internal die sensor" dark={dark}>
              {powered && <ProgressBar value={stats.tempC} max={85} warn={60} danger={75} dark={dark} />}
              {powered && (
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: stats.tempC > 65 ? "#EF4444" : "#22C55E", margin: 0 }}>
                  {stats.tempC > 65 ? "⚠ HIGH" : "✓ NOMINAL"}
                </p>
              )}
            </StatCard>
          </div>

          {/* Row 2: 4 more stat cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16 }}>
            {/* Latency spans 2 */}
            <div style={{ gridColumn: "span 2", background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Live Latency</p>
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 30, fontWeight: 700, color: textMain }}>{powered ? stats.latencyMs.toFixed(0) : "--"}</span>
                <span style={{ color: "#64748B", fontSize: 13 }}>ms</span>
                <span style={{ marginLeft: "auto", fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B" }}>30s window</span>
              </div>
              <div style={{ border: "2px solid #0A0A0A", background: dark ? "#020B14" : "#F0F9FF", padding: 4, boxShadow: "2px 2px 0 #0A0A0A" }}>
                <LatencySpark history={latHistory} dark={dark} />
              </div>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>
                MIC → I2S → FFT → INFER → WS → Node.js round-trip
              </p>
            </div>

            {/* WiFi — fixed width, no overflow */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8, overflow: "hidden" }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>WiFi Signal</p>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700, margin: 0, color: textMain, lineHeight: 1 }}>
                {powered ? stats.wifiRssi : "--"}
                <span style={{ fontSize: 13, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>dBm</span>
              </p>
              {powered && (
                <>
                  <ProgressBar value={Math.abs(stats.wifiRssi) - 30} max={60} warn={40} danger={55} dark={dark} />
                  <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, margin: 0, color: stats.wifiRssi > -65 ? "#22C55E" : stats.wifiRssi > -75 ? "#F59E0B" : "#EF4444" }}>
                    {stats.wifiRssi > -65 ? "STRONG" : stats.wifiRssi > -75 ? "FAIR" : "WEAK"}
                  </p>
                  <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>802.11n 2.4GHz</p>
                </>
              )}
            </div>

            {/* I2S Buffer */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>I2S Buffer</p>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 28, fontWeight: 700, margin: 0, color: textMain, lineHeight: 1 }}>
                {powered ? stats.i2sBufferFill.toFixed(0) : "--"}
                <span style={{ fontSize: 13, fontWeight: 400, color: "#64748B", marginLeft: 4 }}>%</span>
              </p>
              {powered && <ProgressBar value={stats.i2sBufferFill} max={100} warn={80} danger={92} dark={dark} />}
              {powered && (
                <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0 }}>
                  INMP441 DMA ring
                </p>
              )}
            </div>
          </div>

          {/* Row 3: Data Flow + Cloud */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <DataFlowCard inKBs={powered ? stats.dataFlowIn : 0} outKBs={powered ? stats.dataFlowOut : 0} dark={dark} />

            {/* Cloud / WS stats */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
              <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Stream Stats</p>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                {[
                  ["TOTAL SENT", powered ? `${stats.cloudSentMB.toFixed(2)} MB` : "--"],
                  ["AUDIO CAPTURED", powered ? `${stats.audioSentSec}s` : "--"],
                  ["UPLOAD RATE", powered ? `${stats.dataFlowOut.toFixed(1)} KB/s` : "--"],
                  ["WS RECONNECTS", powered ? `${stats.wsReconnects}` : "--"],
                  ["PSRAM FREE", powered ? `${(stats.psramFree / 1024).toFixed(1)} MB` : "--"],
                  ["PKT LOSS", powered ? `${stats.packetLoss.toFixed(1)}%` : "--"],
                ].map(([k, v]) => (
                  <div key={k} style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                    <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 9, color: "#64748B", margin: 0 }}>{k}</p>
                    <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 16, fontWeight: 700, margin: 0, color: textMain }}>{v}</p>
                  </div>
                ))}
              </div>
              <p style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, color: "#64748B", margin: 0, borderTop: "1px dashed #CBD5E1", paddingTop: 8 }}>
                TRANSPORT: WebSocket (plain) · SERVER: Node.js/Express :3001
              </p>
            </div>
          </div>

          {/* Row 4: Confidence + Log */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <ConfidenceMeter score={powered ? stats.confidence : 0} label={powered ? stats.detectedLabel : "idle"} dark={dark} />

            {/* Serial Log */}
            <div style={{ background: cardBg, border, boxShadow: shadow, padding: 14, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <p style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "#38BDF8", margin: 0 }}>Serial Log</p>
                {powered && (
                  <span style={{ fontFamily: "'Space Mono', monospace", fontSize: 10, fontWeight: 700, background: "#22C55E", color: "#fff", padding: "2px 8px", border: "1.5px solid #0A0A0A", boxShadow: "1px 1px 0 #0A0A0A" }}>
                    LIVE
                  </span>
                )}
              </div>
              <div
                style={{
                  flex: 1,
                  background: "#020B14",
                  border: "2px solid #0A0A0A",
                  padding: 10,
                  fontFamily: "'Space Mono', monospace",
                  fontSize: 10,
                  color: "#38BDF8",
                  overflowY: "auto",
                  maxHeight: 200,
                  display: "flex",
                  flexDirection: "column",
                  gap: 2,
                  boxShadow: "2px 2px 0 #0A0A0A",
                }}
              >
                {logLines.map((l, i) => (
                  <p key={i} style={{ margin: 0, color: i === logLines.length - 1 ? "#FFFFFF" : "#38BDF8", opacity: i === logLines.length - 1 ? 1 : 0.75 }}>
                    {l}
                  </p>
                ))}
              </div>
            </div>
          </div>

        </div>
      </div>

      {/* ── Footer ── */}
      <footer
        style={{
          marginTop: 20,
          background: "#0A0A0A",
          border,
          boxShadow: shadow,
          padding: "8px 20px",
          display: "flex",
          flexWrap: "wrap",
          gap: 16,
          alignItems: "center",
          fontFamily: "'Space Mono', monospace",
          fontSize: 10,
          color: "#38BDF8",
        }}
      >
        <span>DORA MONITOR v4.1</span>
        <span style={{ opacity: 0.3 }}>·</span>
        <span style={{ color: "#64748B" }}>ESP32-S3 · MixedNet · WebSocket · Vosk ASR · React+Vite</span>
        <span style={{ marginLeft: "auto", opacity: 0.5 }}>1Hz REFRESH · {powered ? "STREAMING" : "IDLE"}</span>
      </footer>
    </div>
  );
}
