import React, { useEffect, useRef, useState } from 'react'
import './AudioVisualizer.css'

export default function AudioVisualizer() {
  const canvasRef = useRef(null)
  const [audioData, setAudioData] = useState([])

  useEffect(() => {
    const generateAudioData = () => {
      const samples = 64
      const data = []
      for (let i = 0; i < samples; i++) {
        data.push(Math.random() * 100 - 50)
      }
      setAudioData(data)
    }

    const interval = setInterval(generateAudioData, 100)
    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    const width = canvas.width
    const height = canvas.height
    const centerY = height / 2

    // Clear canvas
    ctx.fillStyle = 'rgba(10, 14, 39, 0.5)'
    ctx.fillRect(0, 0, width, height)

    // Draw grid
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.1)'
    ctx.lineWidth = 1
    for (let i = 0; i < 5; i++) {
      const y = (height / 5) * i
      ctx.beginPath()
      ctx.moveTo(0, y)
      ctx.lineTo(width, y)
      ctx.stroke()
    }

    // Draw waveform
    if (audioData.length > 0) {
      ctx.strokeStyle = 'url(#gradient)'
      ctx.lineWidth = 2
      ctx.lineCap = 'round'
      ctx.lineJoin = 'round'

      // Create gradient
      const gradient = ctx.createLinearGradient(0, 0, width, 0)
      gradient.addColorStop(0, 'rgba(0, 212, 255, 0.3)')
      gradient.addColorStop(0.5, 'rgba(114, 9, 183, 0.8)')
      gradient.addColorStop(1, 'rgba(255, 0, 110, 0.3)')
      ctx.strokeStyle = gradient

      ctx.beginPath()
      ctx.moveTo(0, centerY)

      audioData.forEach((sample, i) => {
        const x = (i / audioData.length) * width
        const y = centerY - (sample / 100) * (height / 4)
        ctx.lineTo(x, y)
      })

      ctx.stroke()

      // Draw fill under waveform
      ctx.globalAlpha = 0.2
      ctx.fillStyle = gradient
      ctx.fill()
      ctx.globalAlpha = 1
    }

    // Draw center line
    ctx.strokeStyle = 'rgba(0, 212, 255, 0.2)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, centerY)
    ctx.lineTo(width, centerY)
    ctx.stroke()
  }, [audioData])

  return (
    <div className="card audio-card">
      <div className="card-title">Audio Waveform</div>
      <div className="waveform-container">
        <canvas
          ref={canvasRef}
          width={300}
          height={120}
          className="waveform-canvas"
        ></canvas>
      </div>
      <div className="audio-stats">
        <div className="stat">
          <span className="stat-label">RMS</span>
          <span className="stat-value">{(Math.random() * 50).toFixed(1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Peak</span>
          <span className="stat-value">{(Math.random() * 100).toFixed(1)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Freq</span>
          <span className="stat-value">16kHz</span>
        </div>
      </div>
    </div>
  )
}
