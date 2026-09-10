import React from 'react'
import './DeploymentTimeline.css'

export default function DeploymentTimeline({ currentStep }) {
  const steps = [
    {
      id: 0,
      title: 'Dataset Prep',
      description: 'Audio collection & labeling',
      status: 'completed',
      icon: '📊'
    },
    {
      id: 1,
      title: 'Training',
      description: 'Model optimization',
      status: currentStep >= 1 ? (currentStep > 1 ? 'completed' : 'active') : 'pending',
      icon: '🧠'
    },
    {
      id: 2,
      title: 'Quantization',
      description: 'Int8 compression',
      status: currentStep >= 2 ? (currentStep > 2 ? 'completed' : 'active') : 'pending',
      icon: '⚡'
    },
    {
      id: 3,
      title: 'Hardware Test',
      description: 'Microphone validation',
      status: currentStep >= 3 ? (currentStep > 3 ? 'completed' : 'active') : 'pending',
      icon: '📱'
    },
    {
      id: 4,
      title: 'KWS Integration',
      description: 'Firmware deployment',
      status: currentStep >= 4 ? (currentStep > 4 ? 'completed' : 'active') : 'pending',
      icon: '🔧'
    },
    {
      id: 5,
      title: 'Live Demo',
      description: 'Real-time detection',
      status: currentStep >= 5 ? 'completed' : 'pending',
      icon: '🎯'
    }
  ]

  return (
    <div className="card timeline-card card-wide">
      <div className="card-title">Deployment Pipeline</div>
      <div className="timeline">
        {steps.map((step, idx) => (
          <div key={step.id} className={`timeline-item timeline-${step.status}`}>
            <div className="timeline-marker">
              <div className="marker-icon">{step.icon}</div>
              <div className={`marker-dot status-${step.status}`}></div>
            </div>
            <div className="timeline-content">
              <div className="step-title">{step.title}</div>
              <div className="step-description">{step.description}</div>
            </div>
            {idx < steps.length - 1 && <div className="timeline-line"></div>}
          </div>
        ))}
      </div>
    </div>
  )
}
