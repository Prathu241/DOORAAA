import React, { useState, useEffect } from 'react'
import TrainingMetrics from './components/TrainingMetrics'
import HardwareStatus from './components/HardwareStatus'
import AudioVisualizer from './components/AudioVisualizer'
import ModelChart from './components/ModelChart'
import DeploymentTimeline from './components/DeploymentTimeline'
import KeywordDetector from './components/KeywordDetector'
import './App.css'

export default function App() {
  const [metrics, setMetrics] = useState({
    step: 0,
    accuracy: 0,
    recall: 0,
    precision: 0,
    loss: 0,
    batchNum: 0,
    trainingSince: Date.now()
  })

  const [hardware, setHardware] = useState({
    esp32Status: 'disconnected',
    microphoneStatus: 'not_tested',
    portName: 'COM3',
    signalStrength: 0,
    temperature: 32,
    firmwareVersion: '1.0.0'
  })

  const [historicalData, setHistoricalData] = useState([])

  // Simulate metrics polling
  useEffect(() => {
    const interval = setInterval(() => {
      setMetrics(prev => ({
        ...prev,
        step: prev.step + Math.random() * 50,
        accuracy: Math.min(0.999, prev.accuracy + Math.random() * 0.01),
        recall: Math.min(0.999, prev.recall + Math.random() * 0.01),
        precision: Math.min(0.999, prev.precision + Math.random() * 0.01),
        loss: Math.max(0.001, prev.loss - Math.random() * 0.005),
        batchNum: prev.batchNum + 1
      }))
    }, 3000)

    return () => clearInterval(interval)
  }, [])

  // Update historical data
  useEffect(() => {
    setHistoricalData(prev => [...prev.slice(-99), metrics])
  }, [metrics])

  return (
    <div className="app">
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <div className="logo-icon">🎤</div>
            <h1>DORA KWS</h1>
            <span className="tagline">Real-Time Keyword Spotting Dashboard</span>
          </div>
          <div className="status-indicator">
            <div className={`dot ${metrics.step > 0 ? 'active' : ''}`}></div>
            <span>{metrics.step > 0 ? 'Training Active' : 'Ready'}</span>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="grid-container">
          {/* Top Row - Key Metrics */}
          <TrainingMetrics metrics={metrics} />

          {/* Middle Left - Hardware Status */}
          <HardwareStatus hardware={hardware} setHardware={setHardware} />

          {/* Middle Right - Audio Visualizer */}
          <AudioVisualizer />

          {/* Bottom - Charts */}
          <ModelChart data={historicalData} />

          {/* Timeline */}
          <DeploymentTimeline currentStep={Math.min(5, Math.floor(metrics.step / 2000))} />

          {/* Keyword Detection */}
          <KeywordDetector metrics={metrics} />
        </div>
      </main>

      <footer className="footer">
        <div className="footer-content">
          <p>DORA MixedNet KWS • ESP32-S3 + INMP441 • 4-Hour Deployment Sprint</p>
          <p className="training-time">
            Training for: {Math.floor((Date.now() - metrics.trainingSince) / 1000 / 60)} minutes
          </p>
        </div>
      </footer>
    </div>
  )
}
