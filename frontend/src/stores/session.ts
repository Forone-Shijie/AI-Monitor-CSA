/**
 * Session Store - Pinia store for session management
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  SessionInfo,
  SessionCreate,
  SessionUpdate,
  MonitoringFrame,
  MonitoringStatus,
  Alert,
  RealtimeScores
} from '@/types/api'
import { SessionStatus } from '@/types/api'
import * as api from '@/services/api'
import { wsClient } from '@/services/websocket'

export const useSessionStore = defineStore('session', () => {
  // State
  const sessions = ref<SessionInfo[]>([])
  const activeSession = ref<SessionInfo | null>(null)
  const monitoringStatus = ref<MonitoringStatus | null>(null)
  const currentFrame = ref<MonitoringFrame | null>(null)
  const frameHistory = ref<MonitoringFrame[]>([])
  const alerts = ref<Alert[]>([])
  const isConnected = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const hasActiveSession = computed(() => activeSession.value !== null)

  const isRunning = computed(() =>
    activeSession.value?.status === SessionStatus.RUNNING
  )

  const currentScores = computed<RealtimeScores>(() =>
    monitoringStatus.value?.scores ?? {
      pose: 0,
      action: 0,
      communication: 0,
      total: 0
    }
  )

  const recentAlerts = computed(() =>
    alerts.value.slice(-10).reverse()
  )

  // Actions
  async function fetchSessions(traineeId?: string) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.listSessions(traineeId)
      sessions.value = response.data ?? []
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch sessions'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function createSession(data: SessionCreate) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.createSession(data)
      if (response.success && response.data) {
        sessions.value.unshift(response.data)
        activeSession.value = response.data
        return response.data
      }
      throw new Error(response.message || 'Failed to create session')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function loadSession(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      const session = await api.getSession(sessionId)
      activeSession.value = session
      return session
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function startSession(sessionId: string, triggerType: string = 'manual') {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.startSession(sessionId, triggerType)
      if (response.success && response.data) {
        activeSession.value = response.data
        await connectWebSocket(sessionId)
        return response.data
      }
      throw new Error(response.message || 'Failed to start session')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function stopSession(sessionId: string, generateReport: boolean = true) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.stopSession(sessionId, generateReport)
      if (response.success && response.data) {
        disconnectWebSocket()
        // Clear activeSession so Dashboard doesn't show "current training"
        activeSession.value = null
        return response.data
      }
      throw new Error(response.message || 'Failed to stop session')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to stop session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function pauseSession(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.pauseSession(sessionId)
      if (response.success && response.data) {
        activeSession.value = response.data
        return response.data
      }
      throw new Error(response.message || 'Failed to pause session')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to pause session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function cancelSession(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.cancelSession(sessionId)
      if (response.success && response.data) {
        activeSession.value = response.data
        disconnectWebSocket()
        return response.data
      }
      throw new Error(response.message || 'Failed to cancel session')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to cancel session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function deleteSession(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.deleteSession(sessionId)
      if (response.success) {
        sessions.value = sessions.value.filter(s => s.session_id !== sessionId)
        if (activeSession.value?.session_id === sessionId) {
          activeSession.value = null
          disconnectWebSocket()
        }
      }
      return response
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateSession(sessionId: string, data: SessionUpdate) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.updateSession(sessionId, data)
      if (response.success && response.data) {
        // Update in sessions list
        const index = sessions.value.findIndex(s => s.session_id === sessionId)
        if (index !== -1) {
          sessions.value[index] = response.data
        }
        // Update active session if it's the same
        if (activeSession.value?.session_id === sessionId) {
          activeSession.value = response.data
        }
        return response.data
      }
      throw new Error(response.message || 'Failed to update session')
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update session'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchMonitoringStatus(sessionId: string) {
    try {
      monitoringStatus.value = await api.getMonitoringStatus(sessionId)
      return monitoringStatus.value
    } catch (e) {
      console.error('Failed to fetch monitoring status:', e)
      return null
    }
  }

  // WebSocket management
  async function connectWebSocket(sessionId: string) {
    try {
      await wsClient.connect(sessionId)
      isConnected.value = true

      // Register handlers
      wsClient.onFrame((frame) => {
        currentFrame.value = frame
        frameHistory.value.push(frame)
        // Keep only last 1000 frames
        if (frameHistory.value.length > 1000) {
          frameHistory.value.shift()
        }
      })

      wsClient.onStatus((status) => {
        monitoringStatus.value = status
      })

      wsClient.onAlert((alert) => {
        alerts.value.push(alert)
        // Keep only last 100 alerts
        if (alerts.value.length > 100) {
          alerts.value.shift()
        }
      })

      wsClient.onDisconnect(() => {
        isConnected.value = false
      })

      wsClient.onConnect(() => {
        isConnected.value = true
      })

    } catch (e) {
      console.error('Failed to connect WebSocket:', e)
      isConnected.value = false
    }
  }

  function disconnectWebSocket() {
    wsClient.disconnect()
    isConnected.value = false
  }

  // Reset state
  function reset() {
    activeSession.value = null
    monitoringStatus.value = null
    currentFrame.value = null
    frameHistory.value = []
    alerts.value = []
    error.value = null
    disconnectWebSocket()
  }

  function clearAlerts() {
    alerts.value = []
  }

  return {
    // State
    sessions,
    activeSession,
    monitoringStatus,
    currentFrame,
    frameHistory,
    alerts,
    isConnected,
    isLoading,
    error,
    // Computed
    hasActiveSession,
    isRunning,
    currentScores,
    recentAlerts,
    // Actions
    fetchSessions,
    createSession,
    loadSession,
    startSession,
    stopSession,
    pauseSession,
    cancelSession,
    deleteSession,
    updateSession,
    fetchMonitoringStatus,
    connectWebSocket,
    disconnectWebSocket,
    reset,
    clearAlerts
  }
})
