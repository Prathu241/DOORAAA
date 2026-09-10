import React from 'react'
import './TrainingMetrics.css'

export default function TrainingMetrics({ metrics }) {
  const getAccuracyColor = (acc) => {
    if (acc >= 0.98) return 'excellent'
    if (acc >= 0.95) return 'good'
    if (acc >= 0.90) return 'fair'
    return 'poor'
  }

  const formatNumber = (num) => {
    if (typeof num !== 'number') return '0.000'
    return num.toFixed(3)
  }

  const MetricCard = ({ label, value, unit, color, percentage }) => (
    <div className={`metric-card metric-${color}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">
        {typeof value === 'number' ? (value * 100).toFixed(1) : value}
        <span className="metric-unit">{unit}</span>
      </div>
      {percentage !== undefined && (
        <div className="metric-bar">
          <div className="metric-fill" style={{ width: `${percentage * 100}%` }}></div>
        </div>
      )}
    </div>
  )

  return (
    <>
      <MetricCard
        label="Training Step"
        value={Math.floor(metrics.step)}
        unit=""
        color="primary"
      />
      <MetricCard
        label="Accuracy"
        value={metrics.accuracy}
        unit="%"
        color={getAccuracyColor(metrics.accuracy)}
        percentage={metrics.accuracy}
      />
      <MetricCard
        label="Recall"
        value={metrics.recall}
        unit="%"
        color="success"
        percentage={metrics.recall}
      />
      <MetricCard
        label="Precision"
        value={metrics.precision}
        unit="%"
        color="secondary"
        percentage={metrics.precision}
      />
      <MetricCard
        label="Loss"
        value={formatNumber(metrics.loss)}
        unit=""
        color={metrics.loss < 0.05 ? 'success' : 'warning'}
      />
      <MetricCard
        label="Batch"
        value={metrics.batchNum}
        unit=""
        color="primary"
      />
    </>
  )
}
