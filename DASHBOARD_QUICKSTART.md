# DORA Dashboard - Quick Start Guide

## 🚀 Start the Dashboard (5 minutes)

### Option 1: Automatic (PowerShell)

```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm install
npm start
```

Then open: **http://localhost:5000** in your browser

### Option 2: Development Mode (Hot Reload)

Terminal 1:
```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm install
npm run dev
```

Terminal 2 (optional, for real backend data):
```powershell
cd c:\Users\PRATHAM\DORA_MIXED-net\dashboard
npm run server
```

Then open: **http://localhost:5173** in your browser

## 📊 What You'll See

1. **Training Metrics** (Top Left)
   - Live step counter
   - Accuracy % with color coding (green = excellent)
   - Recall & Precision percentages
   - Loss value

2. **Hardware Status** (Middle Left)
   - ESP32-S3 connection indicator
   - INMP441 microphone signal bar
   - Firmware version
   - Device temperature

3. **Audio Waveform** (Middle Center)
   - Real-time audio visualization
   - RMS, Peak, Frequency displays
   - Green-to-blue gradient waveform

4. **Performance Chart** (Bottom)
   - Accuracy vs Training Step
   - Recall and Precision trends
   - Interactive hover tooltips
   - Historical data (last 50 updates)

5. **Deployment Timeline** (Bottom)
   - 6-phase pipeline visualization
   - Current step highlight (glowing dot)
   - Completed phases in green
   - Active phase in cyan

6. **Keyword Detections** (Right)
   - Real-time detection log (top 10)
   - Confidence scores per detection
   - Detection timestamps
   - Audio RMS levels

## 🎨 Design Features

- **Dark Theme**: Easy on the eyes, cinematic feel
- **Glassmorphism**: Frosted glass cards with blur effects
- **Gradients**: Cyan → Purple theme
- **Animations**: Smooth fades, glows, and transitions
- **Responsive**: Works on desktop and tablet

## 🔌 Real Data Connection

The dashboard automatically reads from:
```
c:\Users\PRATHAM\DORA_MIXED-net\training_log_live.txt
```

Make sure this file is being updated by the training process for live metrics.

## 🛠️ Troubleshooting

### "npm command not found"
Install Node.js from: https://nodejs.org/

### "Port 5000 already in use"
Change port in `server.js` line 8:
```js
const PORT = 5001  // Changed from 5000
```

### "No metrics showing"
- Check that `training_log_live.txt` exists
- Ensure training process is running
- Refresh browser page

### "Slow performance"
- Close other browser tabs
- Use Chrome/Edge instead of Firefox
- Disable browser extensions

## 📱 Access from Other Devices

If running on local network:
```
http://your-computer-ip:5000
```

Find your IP:
```powershell
ipconfig | findstr "IPv4"
```

## 🔗 API Endpoints (Backend)

If you need to integrate with other tools:

```bash
GET /api/metrics
GET /api/hardware-status
GET /api/training-progress
GET /api/model-status
```

See `server.js` for details.

## 📚 Project Structure

```
dashboard/
├── src/
│   ├── App.jsx                 # Main React component
│   ├── components/             # 6 dashboard components
│   └── *.css                   # Styling
├── server.js                   # Express backend
├── package.json                # Dependencies
└── README.md                   # Full documentation
```

## 🎯 Next Steps

1. ✅ Dashboard is ready
2. ⏳ Fix ESP32-S3 USB driver issue
3. ⏳ Flash microphone test firmware
4. ⏳ Wait for training to complete & export model
5. ⏳ Integrate KWS model into firmware
6. ⏳ Live hardware testing

Monitor dashboard progress while troubleshooting hardware!

---

**Questions?** Check `dashboard/README.md` for detailed documentation.
