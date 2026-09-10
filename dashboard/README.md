# DORA KWS Dashboard

A real-time, modern dashboard for monitoring DORA Keyword Spotting training, hardware validation, and deployment pipeline.

## Features

✨ **Real-Time Training Metrics**
- Live accuracy, recall, precision, and loss graphs
- Step-by-step progress tracking
- Historical data visualization

🎤 **Audio Monitoring**
- Waveform visualization
- RMS and peak signal detection
- Real-time audio stats

📱 **Hardware Status**
- ESP32-S3 connection monitoring
- INMP441 microphone signal strength
- Temperature and firmware tracking

🎯 **Keyword Detection**
- Live detection events log
- Confidence scores
- Audio RMS levels per detection

🛠️ **Deployment Pipeline**
- 6-step deployment timeline
- Phase completion tracking
- Status indicators (pending/active/completed)

## Tech Stack

- **Frontend**: React 18 + Vite
- **Charts**: Recharts
- **Backend**: Express.js + Node.js
- **Styling**: Modern CSS with glassmorphism effects

## Installation

### Prerequisites
- Node.js 16+ 
- npm or yarn

### Setup

1. Navigate to dashboard directory:
```bash
cd dashboard
```

2. Install dependencies:
```bash
npm install
```

3. Build the dashboard:
```bash
npm run build
```

4. Start the server:
```bash
npm run start
```

The dashboard will be available at `http://localhost:5000`

## Development

For development with hot reload:

1. Start the Vite dev server:
```bash
npm run dev
```

2. In another terminal, start the backend server (if needed for real data):
```bash
npm run server
```

Dashboard will be at `http://localhost:5173`

## Architecture

```
dashboard/
├── src/
│   ├── components/
│   │   ├── TrainingMetrics.jsx    # Real-time metrics cards
│   │   ├── HardwareStatus.jsx     # ESP32 & microphone monitoring
│   │   ├── AudioVisualizer.jsx    # Waveform visualization
│   │   ├── ModelChart.jsx         # Performance graphs
│   │   ├── DeploymentTimeline.jsx # Phase tracking
│   │   └── KeywordDetector.jsx    # Detection event log
│   ├── App.jsx                    # Main application
│   ├── App.css                    # Global styles
│   └── main.jsx                   # Entry point
├── index.html
├── vite.config.js
├── server.js                      # Express backend
├── package.json
└── README.md
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/metrics` | GET | Current training metrics |
| `/api/hardware-status` | GET | ESP32-S3 & microphone status |
| `/api/training-progress` | GET | Historical training data |
| `/api/model-status` | GET | Quantized model file info |

## Styling

The dashboard uses a modern **dark theme** with:
- Glassmorphism effects (backdrop blur)
- Cyan/purple gradient accents
- Smooth animations and transitions
- Responsive grid layout

Colors:
- **Primary**: #00d4ff (cyan)
- **Secondary**: #ff006e (magenta)
- **Accent**: #7209b7 (purple)
- **Success**: #10b981 (green)
- **Background**: #0a0e27 (very dark blue)

## Customization

### Change Theme Colors

Edit `.root` variables in `src/index.css`:
```css
:root {
  --primary: #00d4ff;      /* Main accent color */
  --secondary: #ff006e;    /* Alternative accent */
  --accent: #7209b7;       /* Gradient accent */
  /* ... more colors */
}
```

### Add New Components

Create a new component in `src/components/`:
```jsx
export default function MyComponent() {
  return (
    <div className="card">
      <div className="card-title">My Component</div>
      {/* content */}
    </div>
  )
}
```

Then import and add to `App.jsx`.

## Performance

- Optimized with lazy loading
- Efficient re-renders using React hooks
- Chart updates throttled to prevent lag
- Responsive grid layout with CSS

## Troubleshooting

### Port Already in Use
Change port in `server.js`:
```js
const PORT = 5001 // Change from 5000
```

### Real Data Not Showing
Ensure training log exists at:
```
c:\Users\PRATHAM\DORA_MIXED-net\training_log_live.txt
```

The dashboard will use mock data if the file doesn't exist.

### Graphs Not Rendering
Check browser console for any errors. Ensure recharts is properly installed:
```bash
npm install recharts
```

## Future Enhancements

- WebSocket live updates instead of polling
- Database for historical metric storage
- Export metrics to CSV/JSON
- Alerting system for training anomalies
- Multi-device hardware monitoring
- Audio file upload for testing

## License

MIT
