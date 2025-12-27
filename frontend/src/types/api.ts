/**
 * CC-SOP Monitor API Types
 * TypeScript interfaces matching backend Pydantic models
 */

// =============================================================================
// Enums (as const objects for erasableSyntaxOnly compatibility)
// =============================================================================

export const SessionStatus = {
  CREATED: 'created',
  RUNNING: 'running',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled'
} as const
export type SessionStatus = typeof SessionStatus[keyof typeof SessionStatus]

export const ScenarioType = {
  BRACE_POSITION: 'brace_position',
  FIRE_EMERGENCY: 'fire_emergency',
  EVACUATION: 'evacuation',
  MEDICAL_EMERGENCY: 'medical_emergency',
  SECURITY_THREAT: 'security_threat'
} as const
export type ScenarioType = typeof ScenarioType[keyof typeof ScenarioType]

export const VideoSourceType = {
  CAMERA: 'camera',
  FILE: 'file',
  RTSP: 'rtsp'
} as const
export type VideoSourceType = typeof VideoSourceType[keyof typeof VideoSourceType]

export const ASRMode = {
  ONLINE: 'online',
  OFFLINE: 'offline',
  HYBRID: 'hybrid'
} as const
export type ASRMode = typeof ASRMode[keyof typeof ASRMode]

// =============================================================================
// Session Types
// =============================================================================

export interface SessionCreate {
  trainee_id: string
  trainee_name: string
  scenario_id?: string
  video_source?: VideoSourceType
  video_path?: string
  camera_id?: number
  audio_device_id?: number
}

export interface SessionUpdate {
  trainee_id?: string
  trainee_name?: string
  scenario_id?: string
  camera_id?: number
  audio_device_id?: number
}

// Device info for camera and audio device selection
export interface DeviceInfo {
  id: number
  name: string
}

export interface SessionInfo {
  session_id: string
  trainee_id: string
  trainee_name: string
  scenario_id?: string
  status: SessionStatus
  created_at: string
  started_at?: string
  ended_at?: string
  duration?: number
}

export interface SessionResponse {
  success: boolean
  message: string
  data?: SessionInfo
}

export interface SessionListResponse {
  success: boolean
  message: string
  data: SessionInfo[]
  total: number
}

// =============================================================================
// Monitoring Data Types
// =============================================================================

export interface PoseData {
  timestamp: number
  detected: boolean
  keypoints?: number[][]
  angles?: Record<string, number>
  pose_type?: string
  confidence: number
}

export interface ActionData {
  timestamp: number
  action_id: string
  action_name: string
  confidence: number
  duration?: number
}

export interface ASRData {
  timestamp: number
  text: string
  confidence: number
  is_final: boolean
  language?: string
}

export interface BraceData {
  timestamp: number
  is_valid: boolean
  body_parts: Record<string, BodyPartStatus>
  hold_duration: number
  overall_score: number
}

export interface BodyPartStatus {
  name: string
  is_compliant: boolean
  score: number
  deviation?: number
  message?: string
}

export interface MonitoringFrame {
  frame_number: number
  timestamp: number
  pose?: PoseData
  action?: ActionData
  asr?: ASRData
  brace?: BraceData
  alerts: Alert[]
}

export interface Alert {
  level: 'info' | 'warning' | 'error'
  message: string
  timestamp: number
  source: string
}

export interface MonitoringStatus {
  session_id: string
  is_running: boolean
  frame_count: number
  duration: number
  current_scenario?: string
  alerts: Alert[]
  scores: RealtimeScores
}

export interface RealtimeScores {
  pose: number
  action: number
  communication: number
  total: number
}

// =============================================================================
// Evaluation Types
// =============================================================================

export interface EvaluationData {
  session_id: string
  scenario_id: string
  scores: ScoreBreakdown
  grade: string
  details: EvaluationDetails
  timestamp: string
}

export interface ScoreBreakdown {
  pose: DimensionScore
  action: DimensionScore
  communication: DimensionScore
  total: number
  weighted_total: number
}

export interface DimensionScore {
  score: number
  weight: number
  weighted_score: number
  details: Record<string, number>
}

export interface EvaluationDetails {
  pose_analysis: PoseAnalysisDetail
  action_analysis: ActionAnalysisDetail
  communication_analysis: CommunicationAnalysisDetail
}

export interface PoseAnalysisDetail {
  categories: CategoryScore[]
  stability_score: number
  hold_duration: number
}

export interface CategoryScore {
  category: string
  score: number
  issues: string[]
}

export interface ActionAnalysisDetail {
  steps: StepCompliance[]
  completion_rate: number
  timing_score: number
}

export interface StepCompliance {
  step_id: string
  step_name: string
  status: 'completed' | 'missed' | 'late' | 'early'
  expected_time: number
  actual_time?: number
  time_deviation?: number
}

export interface CommunicationAnalysisDetail {
  terminology_score: number
  timeliness_score: number
  clarity_score: number
  matched_terms: string[]
  missed_terms: string[]
}

// =============================================================================
// Report Types
// =============================================================================

export interface ReportData {
  report_id: string
  session_id: string
  trainee_id: string
  trainee_name: string
  scenario_id: string
  scenario_name: string
  generated_at: string
  session_date: string
  duration_seconds: number
  total_score: number
  grade: string
  pose_score: number
  action_score: number
  communication_score: number
  suggestions: Suggestion[]
  ai_summary: string
  ai_configured: boolean
  ai_provider: string
  ai_notice: string
  strengths: string[]
  improvements: string[]
}

export interface Suggestion {
  category: string
  priority: number
  issue: string
  suggestion: string
  example?: string
}

export interface ReportListResponse {
  success: boolean
  message: string
  data: ReportSummary[]
  total: number
}

export interface ReportSummary {
  report_id: string
  session_id: string
  trainee_name: string
  scenario_name: string
  total_score: number
  grade: string
  generated_at: string
}

export interface ReportResponse {
  success: boolean
  message: string
  data: ReportData
}

// =============================================================================
// Playback Types
// =============================================================================

export interface PlaybackData {
  session_id: string
  frames: MonitoringFrame[]
  total_frames: number
  duration: number
  fps: number
}

export interface TimelineEvent {
  timestamp: number
  type: 'action' | 'alert' | 'asr' | 'pose_change'
  label: string
  data: Record<string, unknown>
}

export interface PlaybackSummary {
  session_id: string
  trainee_name: string
  scenario_name: string
  duration: number
  total_frames: number
  action_count: number
  alert_count: number
  has_evaluation: boolean
}

// =============================================================================
// Config Types
// =============================================================================

export interface SystemConfig {
  video_source: VideoSourceType
  video_path?: string
  camera_id: number
  fps: number
  asr_mode: ASRMode
  pose_confidence_threshold: number
  action_confidence_threshold: number
  weights: EvaluationWeights
}

export interface EvaluationWeights {
  pose: number
  action: number
  communication: number
}

export interface ScenarioConfig {
  id: string
  name: string
  description: string
  trigger_keywords: string[]
  time_limit: number
  steps: ScenarioStep[]
}

export interface ScenarioStep {
  step_id: string
  action_id: string
  action_name: string
  time_limit: number
  required: boolean
}

// =============================================================================
// WebSocket Message Types
// =============================================================================

export interface WSMessage {
  type: 'frame' | 'status' | 'alert' | 'evaluation' | 'error'
  data: MonitoringFrame | MonitoringStatus | Alert | EvaluationData | { message: string }
  timestamp: number
}

// =============================================================================
// API Response Types
// =============================================================================

export interface ApiResponse<T = unknown> {
  success: boolean
  message?: string
  data?: T
  error?: string
}

export interface HealthCheck {
  status: string
  sessions: number
  active_session?: string
}
