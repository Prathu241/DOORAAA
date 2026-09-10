import express from 'express'
import cors from 'cors'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const app = express()
const PORT = 5000

app.use(cors())
app.use(express.json())

// Serve static files
app.use(express.static(path.join(__dirname, 'dist')))

// API endpoints
app.get('/api/metrics', (req, res) => {
  try {
    const logPath = path.join(__dirname, '..', 'training_log_live.txt')
    if (fs.existsSync(logPath)) {
      const content = fs.readFileSync(logPath, 'utf8')
      const lines = content.split('\n')
      const lastLine = lines[lines.length - 2] // Second to last (last is empty)

      // Parse metrics from log line
      const accuracyMatch = lastLine.match(/Accuracy = ([\d.]+)/)
      const recallMatch = lastLine.match(/Recall = ([\d.]+)/)
      const precisionMatch = lastLine.match(/Precision = ([\d.]+)/)
      const lossMatch = lastLine.match(/Loss = ([\d.]+)/)
      const stepMatch = lastLine.match(/Mini-Batch #(\d+)/)

      res.json({
        step: stepMatch ? parseInt(stepMatch[1]) : 0,
        accuracy: accuracyMatch ? parseFloat(accuracyMatch[1]) : 0,
        recall: recallMatch ? parseFloat(recallMatch[1]) : 0,
        precision: precisionMatch ? parseFloat(precisionMatch[1]) : 0,
        loss: lossMatch ? parseFloat(lossMatch[1]) : 0,
        batchNum: stepMatch ? parseInt(stepMatch[1]) : 0,
        trainingSince: Date.now() - 60 * 60 * 1000 // 1 hour ago
      })
    } else {
      res.json({
        step: 0,
        accuracy: 0,
        recall: 0,
        precision: 0,
        loss: 0,
        batchNum: 0,
        trainingSince: Date.now()
      })
    }
  } catch (error) {
    console.error('Error reading metrics:', error)
    res.status(500).json({ error: 'Failed to read metrics' })
  }
})

app.get('/api/hardware-status', (req, res) => {
  res.json({
    esp32Status: 'disconnected',
    microphoneStatus: 'not_tested',
    portName: 'COM3',
    signalStrength: 0,
    temperature: 32,
    firmwareVersion: '1.0.0'
  })
})

app.get('/api/training-progress', (req, res) => {
  try {
    const logPath = path.join(__dirname, '..', 'training_log_live.txt')
    if (fs.existsSync(logPath)) {
      const content = fs.readFileSync(logPath, 'utf8')
      const lines = content.split('\n').filter(l => l.trim())
      
      // Extract last 100 lines for historical data
      const historicalLines = lines.slice(-100)
      const data = historicalLines.map((line, idx) => {
        const accuracyMatch = line.match(/Accuracy = ([\d.]+)/)
        const recallMatch = line.match(/Recall = ([\d.]+)/)
        const precisionMatch = line.match(/Precision = ([\d.]+)/)
        const lossMatch = line.match(/Loss = ([\d.]+)/)

        return {
          step: idx,
          accuracy: accuracyMatch ? parseFloat(accuracyMatch[1]) : 0,
          recall: recallMatch ? parseFloat(recallMatch[1]) : 0,
          precision: precisionMatch ? parseFloat(precisionMatch[1]) : 0,
          loss: lossMatch ? parseFloat(lossMatch[1]) : 0
        }
      })
      
      res.json(data)
    } else {
      res.json([])
    }
  } catch (error) {
    console.error('Error reading training progress:', error)
    res.status(500).json({ error: 'Failed to read training progress' })
  }
})

app.get('/api/model-status', (req, res) => {
  try {
    const modelPath = path.join(
      __dirname,
      '..',
      'trained_models',
      'DORA',
      'tflite_stream_state_internal_quant',
      'stream_state_internal_quant.tflite'
    )
    
    const exists = fs.existsSync(modelPath)
    
    res.json({
      quantized: exists,
      filePath: modelPath,
      fileSize: exists ? fs.statSync(modelPath).size : 0,
      timestamp: exists ? fs.statSync(modelPath).mtime : null
    })
  } catch (error) {
    console.error('Error checking model status:', error)
    res.status(500).json({ error: 'Failed to check model status' })
  }
})

// Catch-all for React routing
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'))
})

app.listen(PORT, () => {
  console.log(`🚀 DORA Dashboard Server running on http://localhost:${PORT}`)
})
