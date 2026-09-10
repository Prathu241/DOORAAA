import React, { useState, useEffect } from 'react'
import './KeywordDetector.css'

export default function KeywordDetector({ metrics }) {
  const [detections, setDetections] = useState([])

  useEffect(() => {
    const simulateDetection = () => {
      if (Math.random() > 0.7) {
        const newDetection = {
          id: Date.now(),
          keyword: 'DORA',
          confidence: (Math.random() * 0.3 + 0.7).toFixed(3),
          timestamp: new Date(),
          rms: (Math.random() * 80 + 20).toFixed(1)
        }
        setDetections(prev => [newDetection, ...prev.slice(0, 9)])
      }
    }

    const interval = setInterval(simulateDetection, 2000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="card detector-card">
      <div className="card-title">Keyword Detections</div>
      <div className="detection-log">
        {detections.length === 0 ? (
          <div className="no-detections">
            <div className="waiting-icon">🔊</div>
            <p>Waiting for detections...</p>
          </div>
        ) : (
          detections.map(detection => (
            <div
              key={detection.id}
              className="detection-item"
              style={{
                animation: `slideIn ${0.3}s ease-out`
              }}
            >
              <div className="detection-header">
                <span className="keyword-badge">{detection.keyword}</span>
                <span className="confidence-badge">
                  {(detection.confidence * 100).toFixed(1)}%
                </span>
              </div>
              <div className="detection-meta">
                <span className="meta-label">RMS:</span>
                <span className="meta-value">{detection.rms}</span>
                <span className="time-label">
                  {detection.timestamp.toLocaleTimeString()}
                </span>
              </div>
              <div className="confidence-bar">
                <div
                  className="confidence-fill"
                  style={{ width: `${detection.confidence * 100}%` }}
                ></div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
