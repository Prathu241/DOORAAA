import React from 'react'
import './HardwareStatus.css'

export default function HardwareStatus({ hardware, setHardware }) {
  const toggleConnection = () => {
    setHardware(prev => ({
      ...prev,
      esp32Status: prev.esp32Status === 'connected' ? 'disconnected' : 'connected',
      signalStrength: prev.esp32Status === 'connected' ? 0 : Math.random() * 100
    }))
  }

  const StatusDot = ({ status }) => {
    const getStatusColor = () => {
      if (status === 'connected') return '#10b981'
      if (status === 'connecting') return '#f59e0b'
      if (status === 'not_tested') return '#a0a0a0'
      return '#ef4444'
    }

    return (
      <div
        className="status-dot"
        style={{
          backgroundColor: getStatusColor(),
          boxShadow: status === 'connected' ? `0 0 10px ${getStatusColor()}` : 'none'
        }}
      />
    )
  }

  return (
    <div className="card hardware-card">
      <div className="card-title">Hardware Status</div>

      <div className="hardware-section">
        <div className="hardware-item">
          <div className="item-header">
            <div className="item-icon">📱</div>
            <div className="item-label">ESP32-S3</div>
            <StatusDot status={hardware.esp32Status} />
          </div>
          <div className="item-details">
            <span className="detail-label">Port:</span>
            <span className="detail-value">{hardware.portName}</span>
          </div>
          <div className="item-details">
            <span className="detail-label">Temp:</span>
            <span className="detail-value">{hardware.temperature}°C</span>
          </div>
          <button className="connect-btn" onClick={toggleConnection}>
            {hardware.esp32Status === 'connected' ? 'Disconnect' : 'Connect'}
          </button>
        </div>

        <div className="hardware-item">
          <div className="item-header">
            <div className="item-icon">🎤</div>
            <div className="item-label">INMP441</div>
            <StatusDot status={hardware.microphoneStatus} />
          </div>
          <div className="signal-bar">
            <div className="signal-fill" style={{ width: `${hardware.signalStrength}%` }}></div>
          </div>
          <div className="signal-label">Signal: {hardware.signalStrength.toFixed(0)}%</div>
        </div>

        <div className="hardware-item">
          <div className="item-header">
            <div className="item-icon">⚙️</div>
            <div className="item-label">Firmware</div>
          </div>
          <div className="item-details">
            <span className="detail-label">Version:</span>
            <span className="detail-value">{hardware.firmwareVersion}</span>
          </div>
        </div>
      </div>

      <div className="hardware-footer">
        <div className="connection-info">
          <span className="info-label">Last Update:</span>
          <span className="info-value">{new Date().toLocaleTimeString()}</span>
        </div>
      </div>
    </div>
  )
}
