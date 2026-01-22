/**
 * CC-SOP Monitor WebSocket Service
 * Real-time monitoring data streaming
 */

import type { WSMessage, MonitoringFrame, MonitoringStatus, Alert } from '@/types/api'

type MessageHandler = (message: WSMessage) => void
type FrameHandler = (frame: MonitoringFrame) => void
type StatusHandler = (status: MonitoringStatus) => void
type AlertHandler = (alert: Alert) => void
type ErrorHandler = (error: Event | Error) => void
type ConnectionHandler = () => void

const WS_BASE_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'

export class WebSocketClient {
  private ws: WebSocket | null = null
  private sessionId: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private autoReconnect = true

  // Event handlers
  private onMessageHandlers: MessageHandler[] = []
  private onFrameHandlers: FrameHandler[] = []
  private onStatusHandlers: StatusHandler[] = []
  private onAlertHandlers: AlertHandler[] = []
  private onErrorHandlers: ErrorHandler[] = []
  private onConnectHandlers: ConnectionHandler[] = []
  private onDisconnectHandlers: ConnectionHandler[] = []

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get currentSessionId(): string | null {
    return this.sessionId
  }

  /**
   * Connect to WebSocket for a session
   */
  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        if (this.sessionId === sessionId) {
          resolve()
          return
        }
        this.disconnect()
      }

      this.sessionId = sessionId
      const url = `${WS_BASE_URL}/api/ws/live/${sessionId}`

      try {
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          console.log(`WebSocket connected to session: ${sessionId}`)
          this.reconnectAttempts = 0
          this.onConnectHandlers.forEach(handler => handler())
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message: WSMessage = JSON.parse(event.data)
            this.handleMessage(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.onErrorHandlers.forEach(handler => handler(error))
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('WebSocket disconnected')
          this.onDisconnectHandlers.forEach(handler => handler())
          this.attemptReconnect()
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    this.autoReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.sessionId = null
    this.reconnectAttempts = 0
  }

  /**
   * Send a JSON message to the server
   */
  send(message: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message))
    } else {
      console.warn('WebSocket is not connected')
    }
  }

  /**
   * Send binary frame data to the server
   */
  sendFrame(frameData: Blob | ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(frameData)
    } else {
      console.warn('WebSocket is not connected, cannot send frame')
    }
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(message: WSMessage): void {
    // Call generic handlers
    this.onMessageHandlers.forEach(handler => handler(message))

    // Call type-specific handlers
    switch (message.type) {
      case 'frame':
        this.onFrameHandlers.forEach(handler => handler(message.data as MonitoringFrame))
        break
      case 'status':
        this.onStatusHandlers.forEach(handler => handler(message.data as MonitoringStatus))
        break
      case 'alert':
        this.onAlertHandlers.forEach(handler => handler(message.data as Alert))
        break
      case 'error':
        console.error('Server error:', (message.data as { message: string }).message)
        break
    }
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(): void {
    if (!this.autoReconnect || !this.sessionId) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      if (this.sessionId) {
        this.connect(this.sessionId).catch(console.error)
      }
    }, delay)
  }

  // Event handler registration
  onMessage(handler: MessageHandler): () => void {
    this.onMessageHandlers.push(handler)
    return () => {
      this.onMessageHandlers = this.onMessageHandlers.filter(h => h !== handler)
    }
  }

  onFrame(handler: FrameHandler): () => void {
    this.onFrameHandlers.push(handler)
    return () => {
      this.onFrameHandlers = this.onFrameHandlers.filter(h => h !== handler)
    }
  }

  onStatus(handler: StatusHandler): () => void {
    this.onStatusHandlers.push(handler)
    return () => {
      this.onStatusHandlers = this.onStatusHandlers.filter(h => h !== handler)
    }
  }

  onAlert(handler: AlertHandler): () => void {
    this.onAlertHandlers.push(handler)
    return () => {
      this.onAlertHandlers = this.onAlertHandlers.filter(h => h !== handler)
    }
  }

  onError(handler: ErrorHandler): () => void {
    this.onErrorHandlers.push(handler)
    return () => {
      this.onErrorHandlers = this.onErrorHandlers.filter(h => h !== handler)
    }
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.onConnectHandlers.push(handler)
    return () => {
      this.onConnectHandlers = this.onConnectHandlers.filter(h => h !== handler)
    }
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.onDisconnectHandlers.push(handler)
    return () => {
      this.onDisconnectHandlers = this.onDisconnectHandlers.filter(h => h !== handler)
    }
  }

  /**
   * Configure reconnection behavior
   */
  setReconnectOptions(options: {
    autoReconnect?: boolean
    maxAttempts?: number
    delay?: number
  }): void {
    if (options.autoReconnect !== undefined) {
      this.autoReconnect = options.autoReconnect
    }
    if (options.maxAttempts !== undefined) {
      this.maxReconnectAttempts = options.maxAttempts
    }
    if (options.delay !== undefined) {
      this.reconnectDelay = options.delay
    }
  }
}

// Singleton instance
export const wsClient = new WebSocketClient()


/**
 * Streaming WebSocket Client for sending video frames to backend
 *
 * Connects to /ws/stream/{session_id} endpoint for frame processing.
 */
export class StreamingWebSocketClient {
  private ws: WebSocket | null = null
  private sessionId: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private autoReconnect = true

  // Event handlers
  private onResultHandlers: ((result: Record<string, unknown>) => void)[] = []
  private onConnectHandlers: (() => void)[] = []
  private onDisconnectHandlers: (() => void)[] = []
  private onErrorHandlers: ((error: Event | Error) => void)[] = []

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get currentSessionId(): string | null {
    return this.sessionId
  }

  /**
   * Connect to streaming WebSocket for a session
   */
  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        if (this.sessionId === sessionId) {
          resolve()
          return
        }
        this.disconnect()
      }

      this.sessionId = sessionId
      const url = `${WS_BASE_URL}/api/ws/stream/${sessionId}`
      console.log(`[StreamingWS] Connecting to: ${url}`)

      try {
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          console.log(`[StreamingWS] Connected to session: ${sessionId}`)
          this.reconnectAttempts = 0
          this.onConnectHandlers.forEach(handler => handler())
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            if (message.type === 'connected') {
              console.log('[StreamingWS] Server confirmed connection:', message.data)
            } else if (message.type === 'frame_result') {
              this.onResultHandlers.forEach(handler => handler(message.data))
            } else if (message.type === 'error') {
              console.error('[StreamingWS] Server error:', message.data)
            }
          } catch (error) {
            console.error('[StreamingWS] Failed to parse message:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('[StreamingWS] WebSocket error:', error)
          this.onErrorHandlers.forEach(handler => handler(error))
          reject(error)
        }

        this.ws.onclose = (event) => {
          console.log(`[StreamingWS] Disconnected, code: ${event.code}, reason: ${event.reason}`)
          this.onDisconnectHandlers.forEach(handler => handler())
          this.attemptReconnect()
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Disconnect from streaming WebSocket
   */
  disconnect(): void {
    this.autoReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.sessionId = null
    this.reconnectAttempts = 0
  }

  /**
   * Send binary frame data to the server for processing
   */
  sendFrame(frameData: Blob | ArrayBuffer): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(frameData)
    } else {
      console.warn('Streaming WebSocket is not connected, cannot send frame')
    }
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(): void {
    if (!this.autoReconnect || !this.sessionId) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max streaming reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = 1000 * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Streaming reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      if (this.sessionId) {
        this.connect(this.sessionId).catch(console.error)
      }
    }, delay)
  }

  // Event handler registration
  onResult(handler: (result: Record<string, unknown>) => void): () => void {
    this.onResultHandlers.push(handler)
    return () => {
      this.onResultHandlers = this.onResultHandlers.filter(h => h !== handler)
    }
  }

  onConnect(handler: () => void): () => void {
    this.onConnectHandlers.push(handler)
    return () => {
      this.onConnectHandlers = this.onConnectHandlers.filter(h => h !== handler)
    }
  }

  onDisconnect(handler: () => void): () => void {
    this.onDisconnectHandlers.push(handler)
    return () => {
      this.onDisconnectHandlers = this.onDisconnectHandlers.filter(h => h !== handler)
    }
  }

  onError(handler: (error: Event | Error) => void): () => void {
    this.onErrorHandlers.push(handler)
    return () => {
      this.onErrorHandlers = this.onErrorHandlers.filter(h => h !== handler)
    }
  }
}

// Singleton instance for streaming
export const streamingClient = new StreamingWebSocketClient()


/**
 * Audio Streaming WebSocket Client for sending audio data to backend
 *
 * Connects to /ws/audio/{session_id} endpoint for ASR processing.
 */
export interface ASRResult {
  session_id: string
  timestamp: number
  text: string
  confidence: number
  language: string
  segments: Array<{
    text: string
    start_time: number
    end_time: number
    confidence: number
  }>
}

export class AudioStreamingWebSocketClient {
  private ws: WebSocket | null = null
  private sessionId: string | null = null
  private reconnectAttempts = 0
  private maxReconnectAttempts = 3
  private autoReconnect = true

  // Event handlers
  private onResultHandlers: ((result: ASRResult) => void)[] = []
  private onConnectHandlers: (() => void)[] = []
  private onDisconnectHandlers: (() => void)[] = []
  private onErrorHandlers: ((error: Event | Error) => void)[] = []

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }

  get currentSessionId(): string | null {
    return this.sessionId
  }

  /**
   * Connect to audio streaming WebSocket for a session
   */
  connect(sessionId: string): Promise<void> {
    return new Promise((resolve, reject) => {
      if (this.ws?.readyState === WebSocket.OPEN) {
        if (this.sessionId === sessionId) {
          resolve()
          return
        }
        this.disconnect()
      }

      this.sessionId = sessionId
      const url = `${WS_BASE_URL}/api/ws/audio/${sessionId}`

      try {
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          console.log(`Audio WebSocket connected to session: ${sessionId}`)
          this.reconnectAttempts = 0
          this.onConnectHandlers.forEach(handler => handler())
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            const message = JSON.parse(event.data)
            if (message.type === 'asr_result') {
              this.onResultHandlers.forEach(handler => handler(message.data as ASRResult))
            }
          } catch (error) {
            console.error('Failed to parse audio message:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('Audio WebSocket error:', error)
          this.onErrorHandlers.forEach(handler => handler(error))
          reject(error)
        }

        this.ws.onclose = () => {
          console.log('Audio WebSocket disconnected')
          this.onDisconnectHandlers.forEach(handler => handler())
          this.attemptReconnect()
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Disconnect from audio WebSocket
   */
  disconnect(): void {
    this.autoReconnect = false
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
    this.sessionId = null
    this.reconnectAttempts = 0
  }

  /**
   * Send PCM audio data to the server for ASR processing
   */
  sendAudio(audioData: ArrayBuffer | Int16Array): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      if (audioData instanceof Int16Array) {
        this.ws.send(audioData.buffer)
      } else {
        this.ws.send(audioData)
      }
    } else {
      console.warn('Audio WebSocket is not connected, cannot send audio')
    }
  }

  /**
   * Attempt to reconnect
   */
  private attemptReconnect(): void {
    if (!this.autoReconnect || !this.sessionId) return
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max audio reconnect attempts reached')
      return
    }

    this.reconnectAttempts++
    const delay = 1000 * Math.pow(2, this.reconnectAttempts - 1)

    console.log(`Audio reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)

    setTimeout(() => {
      if (this.sessionId) {
        this.connect(this.sessionId).catch(console.error)
      }
    }, delay)
  }

  // Event handler registration
  onResult(handler: (result: ASRResult) => void): () => void {
    this.onResultHandlers.push(handler)
    return () => {
      this.onResultHandlers = this.onResultHandlers.filter(h => h !== handler)
    }
  }

  onConnect(handler: () => void): () => void {
    this.onConnectHandlers.push(handler)
    return () => {
      this.onConnectHandlers = this.onConnectHandlers.filter(h => h !== handler)
    }
  }

  onDisconnect(handler: () => void): () => void {
    this.onDisconnectHandlers.push(handler)
    return () => {
      this.onDisconnectHandlers = this.onDisconnectHandlers.filter(h => h !== handler)
    }
  }

  onError(handler: (error: Event | Error) => void): () => void {
    this.onErrorHandlers.push(handler)
    return () => {
      this.onErrorHandlers = this.onErrorHandlers.filter(h => h !== handler)
    }
  }
}

// Singleton instance for audio streaming
export const audioStreamingClient = new AudioStreamingWebSocketClient()
