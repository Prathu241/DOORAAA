# DORA Dashboard - Features & Design

## 🎨 Visual Design

### Color Scheme
```
Primary (Accent):     #00d4ff (Bright Cyan)
Secondary:            #ff006e (Magenta)
Accent:               #7209b7 (Purple)
Success:              #10b981 (Green)
Warning:              #f59e0b (Orange)
Error:                #ef4444 (Red)
Background:           #0a0e27 (Very Dark Blue)
Card Background:      #1a1f3a (Dark Blue)
Border:               #2d3561 (Darker Blue)
Text Primary:         #e0e0e0 (Light Gray)
Text Secondary:       #a0a0a0 (Medium Gray)
```

### Design Elements

**Glassmorphism**
- Frosted glass cards with 10px blur
- Semi-transparent backgrounds (50% opacity)
- Subtle borders with cyan glow
- Hover effects with increased glow

**Typography**
- Headers: 28px, Bold, Gradient text
- Titles: 12px uppercase, letter-spacing
- Values: 24px, gradient text
- Body: 12px, light gray

**Animations**
- Fade-in on mount (0.5s)
- Smooth color transitions (0.3s)
- Pulse effect on active indicators
- Bounce animation on detecting waiting
- Slide-in for new detection events

## 📊 Component Breakdown

### 1. Training Metrics (6 Cards)
**Location**: Top row, grid layout

```
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ STEP 2400   │ │ ACC. 99.4%  │ │ RECALL 97%  │
│ 2400        │ │ ▓▓▓▓▓▓▓░░░  │ │ ▓▓▓▓▓▓░░░░  │
└─────────────┘ └─────────────┘ └─────────────┘

┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ PRECISION   │ │ LOSS        │ │ BATCH       │
│ 98.5%       │ │ 0.015       │ │ 412         │
│ ▓▓▓▓▓▓▓░░░  │ │ (green)     │ │             │
└─────────────┘ └─────────────┘ └─────────────┘
```

**Features**:
- Real-time values update every 3 seconds
- Color-coded accuracy (excellent/good/fair/poor)
- Progress bars for percentages
- Cyan-to-purple gradient text

### 2. Hardware Status Panel
**Location**: Middle left

```
┌─────────────────────────┐
│ HARDWARE STATUS         │
│                         │
│ 📱 ESP32-S3            │
│ [●] Connected          │
│ Port: COM3             │
│ Temp: 32°C             │
│ [Connect Button]       │
│                         │
│ 🎤 INMP441             │
│ [●] Not Tested         │
│ Signal: ▓▓▓░░░░░ 35%   │
│                         │
│ ⚙️ FIRMWARE             │
│ Version: 1.0.0         │
│                         │
│ Last Update: 14:32:45  │
└─────────────────────────┘
```

**Features**:
- Live connection indicator dots
- Color-coded status (green/yellow/gray/red)
- Glowing effect for connected devices
- Signal strength bar
- One-click connect/disconnect button

### 3. Audio Waveform Visualizer
**Location**: Middle center

```
┌──────────────────────┐
│ AUDIO WAVEFORM       │
│                      │
│      ╱╲    ╱╲       │
│    ╱    ╲╱    ╲     │ ← Cyan-to-purple gradient
│  ╱                ╲  │
│ ─────────────────── │ ← Center line
│  ╲                ╱  │
│    ╲    ╱╲    ╱     │
│      ╲╱    ╲╱       │
│                      │
│ RMS: 45.2  Peak: 92  │
│ Freq: 16kHz          │
└──────────────────────┘
```

**Features**:
- Real-time waveform rendering on canvas
- 64 audio samples updated every 100ms
- Grid background
- Center zero line
- Three statistics (RMS, Peak, Frequency)

### 4. Model Performance Chart
**Location**: Bottom, wide (2 columns)

```
┌────────────────────────────────────────┐
│ MODEL PERFORMANCE METRICS              │
│                                        │
│ 100% ┤     ╱─────────────────────     │
│      │    ╱                  ╱  ╲    │
│  80% ├───╱──────────────────╱────╲─  │
│      │  ╱                                │
│  60% ├─╱─────────────────────────      │
│      │╱                                  │
│  40% ├──────────────────────────────    │
│      │                                  │
│  20% ├──────────────────────────────    │
│      │                                  │
│   0% └──────────────────────────────────
│      0   5  10  15  20  25  30  35  40
│      Step
│      ───── Accuracy (cyan)
│      ───── Recall (green)
│      ───── Precision (magenta)
└────────────────────────────────────────┘
```

**Features**:
- Three overlaid line charts
- Interactive tooltips on hover
- Color-coded legends
- 50-step history shown
- Smooth animation of new data points

### 5. Deployment Timeline
**Location**: Bottom, wide (2 columns)

```
┌────────────────────────────────────────┐
│ DEPLOYMENT PIPELINE                    │
│                                        │
│ ● ✓ Dataset Prep                     │
│   Audio collection & labeling          │
│                                        │
│ ◉ ✓ Training                          │
│   Model optimization                   │ ← Active/Glowing
│                                        │
│ ● ○ Quantization                      │
│   Int8 compression                     │
│                                        │
│ ● ○ Hardware Test                     │
│   Microphone validation                │
│                                        │
│ ● ○ KWS Integration                   │
│   Firmware deployment                  │
│                                        │
│ ● ○ Live Demo                         │
│   Real-time detection                  │
└────────────────────────────────────────┘
```

**Features**:
- 6-phase pipeline
- Visual progression indicators
- Green checkmarks for completed
- Cyan glow for active phase
- Gray for pending phases
- Connecting lines between phases

### 6. Keyword Detection Log
**Location**: Right side

```
┌──────────────────────┐
│ KEYWORD DETECTIONS   │
│                      │
│ [DORA] 92.3% ← Badge │
│ RMS: 65.4 14:32:45   │
│ ▓▓▓▓▓▓▓▓░░░░░░░░░░  │
│                      │
│ [DORA] 88.7%         │
│ RMS: 58.2 14:31:15   │
│ ▓▓▓▓▓▓░░░░░░░░░░░░  │
│                      │
│ [DORA] 95.1%         │
│ RMS: 72.1 14:30:45   │
│ ▓▓▓▓▓▓▓▓▓░░░░░░░░░  │
│                      │
│ Waiting for events...│
│ 🔊                   │
└──────────────────────┘
```

**Features**:
- Live detection event log (top 10 shown)
- Keyword badges with gradient
- Confidence percentage badges
- Audio RMS values
- Precise timestamps
- Confidence bars
- Waiting animation when idle

## 🎯 Layout Behavior

### Desktop (1600px+)
```
┌────────────────────────────────────────┐
│ HEADER - Logo | Status Indicator       │
├────────────────────────────────────────┤
│ [Metric] [Metric] [Metric]  [HW]      │
│ [Metric] [Metric] [Metric]  [Audio]   │
│ [Chart - Wide Spanning 2 Cols] [Det]  │
│ [Timeline - Wide Spanning 2 Cols]     │
├────────────────────────────────────────┤
│ FOOTER - Info | Training Time          │
└────────────────────────────────────────┘
```

### Tablet (768px - 1200px)
- Cards auto-wrap to single column
- Charts and timelines full width
- Detections panel below
- Optimized touch interactions

### Mobile (< 768px)
- Everything single column
- Full-width cards
- Larger touch targets
- Bottom navigation

## 🌈 Interactive Elements

### Hover Effects
- Card: Border brightens, shadow glows, lifts up 2px
- Buttons: Color shifts, shadow expands, lifts up
- Metric Bars: Fill width animates smoothly
- Chart: Tooltip appears with data

### Status Indicators
- **Connected** (Green): Solid dot, glowing effect
- **Connecting** (Orange): Pulsing animation
- **Disconnected** (Red): Dim dot, no glow
- **Pending** (Gray): Faint dot

### Animation Timings
- Transitions: 0.3s cubic-bezier
- Fades: 0.5s ease-in-out
- Pulses: 2s infinite ease-in-out
- Data updates: Smooth every 3s

## 📐 Responsive Grid

```css
grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))
gap: 20px
grid-auto-flow: dense
```

This creates 1-3 columns depending on screen width, with cards flowing naturally.

## 🎬 Animations

**Page Load**
```css
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
```

**Active Indicators**
```css
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
```

**Hover Lift**
```css
transform: translateY(-2px);
box-shadow: 0 10px 25px rgba(0, 212, 255, 0.3);
```

## 🔧 Customization Examples

### Change Primary Color
Edit `src/index.css`:
```css
:root {
  --primary: #00d4ff;  /* Change this */
  --secondary: #ff006e;
  --accent: #7209b7;
}
```

### Adjust Animation Speed
Edit component CSS files:
```css
transition: all 0.5s ease;  /* Increase from 0.3s */
```

### Change Chart Colors
Edit `ModelChart.jsx`:
```jsx
<stop offset="5%" stopColor="#00d4ff" />  /* Change color */
```

## 🎓 CSS Architecture

- **Global**: `src/index.css` - Colors, fonts, animations
- **App**: `src/App.css` - Layout, header, footer
- **Components**: Individual CSS files per component
- **Utility Classes**: `.glass`, `.glow`, `.pulse`, `.fade-in`

## 📦 Bundle Size

Optimized for fast loading:
- React + ReactDOM: ~42KB
- Recharts: ~250KB
- CSS: ~15KB
- Total: ~307KB (gzipped)

---

For more details, see `README.md` or run `npm run build` to generate production files.
