/**
 * CC-SOP Monitor API Service
 * Axios-based HTTP client for backend API
 */

import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type {
  SessionCreate,
  SessionUpdate,
  SessionInfo,
  SessionResponse,
  SessionListResponse,
  MonitoringStatus,
  EvaluationData,
  ReportData,
  ReportListResponse,
  ReportResponse,
  PlaybackData,
  PlaybackSummary,
  TimelineEvent,
  SystemConfig,
  ScenarioConfig,
  EvaluationWeights,
  HealthCheck,
  ASRMode,
  DeviceInfo
} from '@/types/api'

// API Base URL
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Create Axios instance
const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem('auth_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// Response interceptor
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    console.error('API Error:', error.message)
    return Promise.reject(error)
  }
)

// =============================================================================
// Health & Root
// =============================================================================

export async function checkHealth(): Promise<HealthCheck> {
  const response = await apiClient.get<HealthCheck>('/health')
  return response.data
}

export async function getApiInfo(): Promise<{ name: string; version: string; status: string }> {
  const response = await apiClient.get('/')
  return response.data
}

// =============================================================================
// Sessions API
// =============================================================================

export async function createSession(data: SessionCreate): Promise<SessionResponse> {
  const response = await apiClient.post<SessionResponse>('/api/sessions', data)
  return response.data
}

export async function listSessions(traineeId?: string): Promise<SessionListResponse> {
  const params = traineeId ? { trainee_id: traineeId } : {}
  const response = await apiClient.get<SessionListResponse>('/api/sessions', { params })
  return response.data
}

export async function getSession(sessionId: string): Promise<SessionInfo> {
  const response = await apiClient.get<SessionInfo>(`/api/sessions/${sessionId}`)
  return response.data
}

export async function deleteSession(sessionId: string): Promise<SessionResponse> {
  const response = await apiClient.delete<SessionResponse>(`/api/sessions/${sessionId}`)
  return response.data
}

export async function updateSession(sessionId: string, data: SessionUpdate): Promise<SessionResponse> {
  const response = await apiClient.put<SessionResponse>(`/api/sessions/${sessionId}`, data)
  return response.data
}

export async function startSession(
  sessionId: string,
  triggerType: string = 'manual'
): Promise<SessionResponse> {
  const response = await apiClient.post<SessionResponse>(`/api/sessions/${sessionId}/start`, {
    trigger_type: triggerType
  })
  return response.data
}

export async function stopSession(
  sessionId: string,
  generateReport: boolean = true
): Promise<SessionResponse> {
  const response = await apiClient.post<SessionResponse>(`/api/sessions/${sessionId}/stop`, {
    generate_report: generateReport
  })
  return response.data
}

export async function pauseSession(sessionId: string): Promise<SessionResponse> {
  const response = await apiClient.post<SessionResponse>(`/api/sessions/${sessionId}/pause`)
  return response.data
}

export async function cancelSession(sessionId: string): Promise<SessionResponse> {
  const response = await apiClient.post<SessionResponse>(`/api/sessions/${sessionId}/cancel`)
  return response.data
}

export async function getMonitoringStatus(sessionId: string): Promise<MonitoringStatus> {
  const response = await apiClient.get<MonitoringStatus>(`/api/sessions/${sessionId}/status`)
  return response.data
}

// =============================================================================
// Evaluation API
// =============================================================================

export async function getEvaluation(sessionId: string): Promise<EvaluationData> {
  const response = await apiClient.get<EvaluationData>(`/api/evaluation/${sessionId}`)
  return response.data
}

export async function runEvaluation(sessionId: string): Promise<EvaluationData> {
  const response = await apiClient.post<EvaluationData>(`/api/evaluation/${sessionId}`)
  return response.data
}

export async function listReports(
  traineeId?: string,
  limit: number = 10
): Promise<ReportListResponse> {
  const params: Record<string, string | number> = { limit }
  if (traineeId) params.trainee_id = traineeId
  const response = await apiClient.get<ReportListResponse>('/api/reports', { params })
  return response.data
}

export async function getReport(reportId: string): Promise<ReportData> {
  const response = await apiClient.get<ReportResponse>(`/api/reports/${reportId}`)
  return response.data.data
}

export async function getDemoReport(type: 'perfect' | 'improvement'): Promise<ReportData> {
  const response = await apiClient.get<ReportResponse>(`/api/reports/demo/${type}`)
  return response.data.data
}

// =============================================================================
// Playback API
// =============================================================================

export async function getPlaybackData(
  sessionId: string,
  startFrame: number = 0,
  endFrame?: number
): Promise<PlaybackData> {
  const params: Record<string, number> = { start_frame: startFrame }
  if (endFrame !== undefined) params.end_frame = endFrame
  const response = await apiClient.get<PlaybackData>(`/api/playback/${sessionId}`, { params })
  return response.data
}

export async function getPlaybackFrames(
  sessionId: string,
  startFrame: number = 0,
  count: number = 100
): Promise<PlaybackData> {
  const response = await apiClient.get<PlaybackData>(`/api/playback/${sessionId}/frames`, {
    params: { start_frame: startFrame, count }
  })
  return response.data
}

export async function getPlaybackTimeline(sessionId: string): Promise<TimelineEvent[]> {
  const response = await apiClient.get<TimelineEvent[]>(`/api/playback/${sessionId}/timeline`)
  return response.data
}

export async function getPlaybackSummary(sessionId: string): Promise<PlaybackSummary> {
  const response = await apiClient.get<PlaybackSummary>(`/api/playback/${sessionId}/summary`)
  return response.data
}

// =============================================================================
// Config API
// =============================================================================

export async function getConfig(): Promise<SystemConfig> {
  const response = await apiClient.get<{ success: boolean; data: SystemConfig }>('/api/config')
  return response.data.data
}

export async function updateConfig(config: Partial<SystemConfig>): Promise<SystemConfig> {
  const response = await apiClient.put<{ success: boolean; data: SystemConfig }>('/api/config', config)
  return response.data.data
}

export async function getScenarios(): Promise<ScenarioConfig[]> {
  const response = await apiClient.get<{ success: boolean; data: ScenarioConfig[] }>('/api/config/scenarios')
  return response.data.data ?? []
}

export async function getScenario(scenarioId: string): Promise<ScenarioConfig> {
  const response = await apiClient.get<{ success: boolean; data: ScenarioConfig }>(`/api/config/scenarios/${scenarioId}`)
  return response.data.data
}

export async function getWeights(): Promise<EvaluationWeights> {
  const response = await apiClient.get<{ success: boolean; data: EvaluationWeights }>('/api/config/weights')
  return response.data.data
}

export async function updateWeights(weights: EvaluationWeights): Promise<EvaluationWeights> {
  const response = await apiClient.put<{ success: boolean; data: EvaluationWeights }>('/api/config/weights', weights)
  return response.data.data
}

export async function getASRModes(): Promise<{ current: string; available: { id: string; name: string }[] }> {
  const response = await apiClient.get<{ success: boolean; data: { current: string; available: { id: string; name: string }[] } }>('/api/config/asr-modes')
  return response.data.data
}

export async function setASRMode(mode: ASRMode): Promise<{ mode: ASRMode }> {
  const response = await apiClient.put<{ mode: ASRMode }>('/api/config/asr-modes', { mode })
  return response.data
}

// =============================================================================
// Device API
// =============================================================================

export async function getCameras(): Promise<DeviceInfo[]> {
  const response = await apiClient.get<{ success: boolean; data: DeviceInfo[] }>('/api/config/cameras')
  return response.data.data ?? []
}

export async function getAudioDevices(): Promise<DeviceInfo[]> {
  const response = await apiClient.get<{ success: boolean; data: DeviceInfo[] }>('/api/config/audio-devices')
  return response.data.data ?? []
}

// Export client for custom requests
export { apiClient }
