<script setup lang="ts">
/**
 * VideoAnalyzer View
 * Analyze uploaded video with skeleton overlay visualization
 *
 * Key features:
 * - Play uploaded video
 * - Capture frames and send to backend for pose detection
 * - Display skeleton overlay on video
 * - Playback controls (play/pause, seek, speed)
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useVideoStore } from '@/stores/video'
import ScorePanel from '@/components/monitoring/ScorePanel.vue'
import AlertPanel from '@/components/monitoring/AlertPanel.vue'
import SkeletonOverlay from '@/components/monitoring/SkeletonOverlay.vue'
import ActionTimeline from '@/components/monitoring/ActionTimeline.vue'
import ReportLoadingModal from '@/components/common/ReportLoadingModal.vue'
import { streamingClient } from '@/services/websocket'
import { captureVideoFrame } from '@/services/mediaDevices'
import { getVideoStreamUrl } from '@/services/api'
import type { PoseData, ActionData, MonitoringFrame } from '@/types/api'

const route = useRoute()
const router = useRouter()
const sessionStore = useSessionStore()
const videoStore = useVideoStore()

// Video element refs
const videoRef = ref<HTMLVideoElement | null>(null)
const videoContainerRef = ref<HTMLDivElement | null>(null)
const videoWidth = ref(640)
const videoHeight = ref(480)
const actualVideoRect = ref({ x: 0, y: 0, width: 640, height: 480 })

// Video state
const videoId = computed(() => route.query.videoId as string || '')
const videoSrc = computed(() => videoId.value ? getVideoStreamUrl(videoId.value) : '')
const isVideoReady = ref(false)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const playbackRate = ref(1.0)

// Session state
const sessionDuration = ref(0)
const durationInterval = ref<number | null>(null)

// Frame capture with adaptive FPS
const frameCapturerRequestId = ref<number | null>(null)
const minFps = 8
const maxFps = 15
let currentFps = maxFps
let captureInterval = 1000 / currentFps  // 可变的帧间隔

// Streaming
const isStreamConnected = ref(false)
const streamResultUnsubscribe = ref<(() => void) | null>(null)

// Report loading modal
const showReportLoading = ref(false)
const loadingModalRef = ref<InstanceType<typeof ReportLoadingModal> | null>(null)

// Local frame data for skeleton display (from streaming result)
const localCurrentFrame = ref<MonitoringFrame | null>(null)

// Track streaming connection status
streamingClient.onConnect(() => { isStreamConnected.value = true })
streamingClient.onDisconnect(() => { isStreamConnected.value = false })

const isRunning = computed(() => sessionStore.isRunning)

// Multi-person support: return poses array
// Prefer local frame data from streaming, fallback to session store
const currentPoses = computed<PoseData[]>(() => {
  const frame = localCurrentFrame.value || sessionStore.currentFrame
  if (!frame) return []

  if (frame.poses?.poses) {
    return frame.poses.poses
  }

  if (frame.pose?.detected) {
    return [frame.pose]
  }

  return []
})

const actions = computed<ActionData[]>(() => {
  const actionList: ActionData[] = []
  for (const frame of sessionStore.frameHistory) {
    if (frame.action) {
      actionList.push(frame.action)
    }
  }
  return actionList
})

// Video info
const videoInfo = computed(() => {
  if (!videoId.value) return null
  return videoStore.videos.find(v => v.video_id === videoId.value) || null
})

/**
 * Handle video loaded metadata
 */
function onVideoLoaded() {
  const video = videoRef.value
  if (!video) return

  videoWidth.value = video.videoWidth || 640
  videoHeight.value = video.videoHeight || 480
  duration.value = video.duration || 0
  isVideoReady.value = true

  updateVideoRect()
}

/**
 * Update video rect for skeleton positioning
 */
function updateVideoRect() {
  const container = videoContainerRef.value
  const video = videoRef.value
  if (!container || !video) return

  const containerRect = container.getBoundingClientRect()
  const videoAspect = videoWidth.value / videoHeight.value
  const containerAspect = containerRect.width / containerRect.height

  let width: number, height: number, x: number, y: number

  if (containerAspect > videoAspect) {
    height = containerRect.height
    width = height * videoAspect
    x = (containerRect.width - width) / 2
    y = 0
  } else {
    width = containerRect.width
    height = width / videoAspect
    x = 0
    y = (containerRect.height - height) / 2
  }

  actualVideoRect.value = { x, y, width, height }
}

/**
 * Frame capture loop with pending frame tracking to prevent backlog
 */
let lastCaptureTime = 0
let frameSentCount = 0
let frameSkippedCount = 0
let loopLoggedOnce = false
let pendingFrame = false  // 是否有未响应的帧（用于流量控制）

// 重置 pendingFrame 的回调，供 onResult 调用
function markFrameProcessed() {
  pendingFrame = false
}

function frameCapturerLoop(timestamp: number) {
  // 只有停止播放时才退出循环
  if (!isPlaying.value) {
    frameCapturerRequestId.value = null
    console.log('[FrameCapturer] Loop stopped (isPlaying=false)')
    return
  }

  // 首次进入时记录状态
  if (!loopLoggedOnce) {
    console.log('[FrameCapturer] Loop entered:', {
      isPlaying: isPlaying.value,
      isVideoReady: isVideoReady.value,
      wsConnected: streamingClient.isConnected
    })
    loopLoggedOnce = true
  }

  // 如果视频还没准备好，继续等待，不退出循环
  if (!isVideoReady.value) {
    frameCapturerRequestId.value = requestAnimationFrame(frameCapturerLoop)
    return
  }

  if (timestamp - lastCaptureTime >= captureInterval) {
    lastCaptureTime = timestamp

    const video = videoRef.value
    if (video && streamingClient.isConnected && video.readyState >= 2) {
      // 流量控制：如果上一帧还未处理完成，跳过本帧避免积压
      if (pendingFrame) {
        frameSkippedCount++
        // 每跳过30帧记录一次日志
        if (frameSkippedCount % 30 === 1) {
          console.log(`[FrameCapturer] Skipping frame (previous pending), total skipped: ${frameSkippedCount}`)
        }
        frameCapturerRequestId.value = requestAnimationFrame(frameCapturerLoop)
        return
      }

      pendingFrame = true  // 标记帧正在等待处理

      captureVideoFrame(video, 'image/jpeg', 0.7, 1280)  // 缩放到720p(maxWidth=1280)，质量0.7
        .then(blob => {
          if (blob && blob.size > 0) {
            frameSentCount++
            // Log every 30 frames (about every 2 seconds at 15fps)
            if (frameSentCount % 30 === 1) {
              console.log(`[FrameCapturer] Sending frame #${frameSentCount}, size: ${blob.size} bytes, skipped: ${frameSkippedCount}`)
            }
            streamingClient.sendFrame(blob)
          } else {
            pendingFrame = false  // 如果 blob 无效，重置标志
          }
        })
        .catch(err => {
          console.error('[FrameCapturer] Error:', err)
          pendingFrame = false  // 出错时重置标志
        })
    } else if (!streamingClient.isConnected) {
      console.warn('[FrameCapturer] WebSocket not connected, skipping frame')
    }
  }

  frameCapturerRequestId.value = requestAnimationFrame(frameCapturerLoop)
}

function startFrameCapturer() {
  if (frameCapturerRequestId.value) return
  lastCaptureTime = 0
  frameSentCount = 0
  frameSkippedCount = 0
  loopLoggedOnce = false
  pendingFrame = false
  // 重置自适应 FPS 到最大值
  currentFps = maxFps
  captureInterval = 1000 / currentFps
  console.log(`[FrameCapturer] Started with FPS: ${currentFps}`)
  frameCapturerRequestId.value = requestAnimationFrame(frameCapturerLoop)
}

function stopFrameCapturer() {
  if (frameCapturerRequestId.value) {
    cancelAnimationFrame(frameCapturerRequestId.value)
    frameCapturerRequestId.value = null
  }
}

/**
 * Playback controls
 */
function togglePlay() {
  const video = videoRef.value
  if (!video) return

  if (isPlaying.value) {
    video.pause()
    isPlaying.value = false
    stopFrameCapturer()
  } else {
    video.play()
    isPlaying.value = true
    startFrameCapturer()
  }
}

function seekTo(event: Event) {
  const video = videoRef.value
  if (!video) return

  const target = event.target as HTMLInputElement
  const time = parseFloat(target.value)
  video.currentTime = time
  currentTime.value = time
}

function setPlaybackRate(rate: number) {
  const video = videoRef.value
  if (!video) return

  playbackRate.value = rate
  video.playbackRate = rate
}

function onTimeUpdate() {
  const video = videoRef.value
  if (video) {
    currentTime.value = video.currentTime
  }
}

function onVideoEnded() {
  isPlaying.value = false
  stopFrameCapturer()
}

/**
 * Format time to mm:ss
 */
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Start session and connect WebSocket
 */
async function startAnalysis() {
  if (!sessionStore.hasActiveSession || !sessionStore.activeSession) {
    console.error('[VideoAnalyzer] No active session')
    return
  }

  try {
    const sessionId = sessionStore.activeSession.session_id
    console.log('[VideoAnalyzer] Starting analysis, session:', sessionId)

    // Start session
    await sessionStore.startSession(sessionId)
    console.log('[VideoAnalyzer] Session started')

    // Connect streaming WebSocket
    await streamingClient.connect(sessionId)
    console.log('[VideoAnalyzer] Streaming WebSocket connected')

    // Subscribe to results - process skeleton data from streaming
    streamResultUnsubscribe.value = streamingClient.onResult((data: Record<string, unknown>) => {
      // 重置 pendingFrame 标志，允许发送下一帧（流量控制关键）
      markFrameProcessed()

      // 自适应 FPS：根据后端处理时间调整发送频率
      const processingTime = (data.processing_time as number) || 0.05
      if (processingTime > 0.08) {
        // 处理时间 > 80ms，降低 FPS
        currentFps = Math.max(minFps, currentFps - 1)
        captureInterval = 1000 / currentFps
        console.log(`[AdaptiveFPS] Processing slow (${(processingTime * 1000).toFixed(0)}ms), FPS: ${currentFps}`)
      } else if (processingTime < 0.04 && currentFps < maxFps) {
        // 处理时间 < 40ms 且未达到最大 FPS，提高 FPS
        currentFps = Math.min(maxFps, currentFps + 1)
        captureInterval = 1000 / currentFps
        console.log(`[AdaptiveFPS] Processing fast (${(processingTime * 1000).toFixed(0)}ms), FPS: ${currentFps}`)
      }

      // Process frame_result containing skeleton data
      if (data) {
        localCurrentFrame.value = {
          frame_number: (data.frame_number as number) || 0,
          timestamp: (data.timestamp as number) || Date.now() / 1000,
          poses: data.poses as MonitoringFrame['poses'],
          pose: data.pose as MonitoringFrame['pose'],
          alerts: []
        }
      }
    })

    // Start duration timer
    durationInterval.value = window.setInterval(() => {
      sessionDuration.value++
    }, 1000)

    // Start video playback
    togglePlay()
    console.log('[VideoAnalyzer] Analysis started, video playing')

  } catch (error) {
    console.error('[VideoAnalyzer] Failed to start analysis:', error)
  }
}

/**
 * Stop analysis and generate report
 */
async function stopAnalysis(generateReport: boolean = true) {
  if (!sessionStore.activeSession) return

  const sessionId = sessionStore.activeSession.session_id

  // Stop video
  const video = videoRef.value
  if (video) {
    video.pause()
  }
  isPlaying.value = false
  stopFrameCapturer()

  // Stop duration timer
  if (durationInterval.value) {
    clearInterval(durationInterval.value)
    durationInterval.value = null
  }

  // Disconnect streaming
  streamingClient.disconnect()
  if (streamResultUnsubscribe.value) {
    streamResultUnsubscribe.value()
    streamResultUnsubscribe.value = null
  }

  // Show loading modal and stop session
  if (generateReport) {
    showReportLoading.value = true
    const minDisplayTime = 3000 // Minimum 3 seconds for animation
    const startTime = Date.now()

    try {
      await sessionStore.stopSession(sessionId, true)

      // Ensure minimum display time for animation
      const elapsed = Date.now() - startTime
      if (elapsed < minDisplayTime) {
        await new Promise(resolve => setTimeout(resolve, minDisplayTime - elapsed))
      }

      // Trigger completion animation
      if (loadingModalRef.value) {
        loadingModalRef.value.complete()
      }
    } catch (error) {
      console.error('Failed to stop session:', error)
      showReportLoading.value = false
    }
  } else {
    await sessionStore.stopSession(sessionId, false)
    router.push('/')
  }
}

function onReportLoadingComplete() {
  showReportLoading.value = false
  router.push('/reports')
}

// Watch for window resize
function handleResize() {
  updateVideoRect()
}

onMounted(async () => {
  // Fetch videos if not loaded
  if (videoStore.videos.length === 0) {
    await videoStore.fetchVideos()
  }

  window.addEventListener('resize', handleResize)

  // Check if we have a valid video
  if (!videoId.value) {
    console.error('No video ID provided')
    router.push('/')
    return
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stopFrameCapturer()

  if (durationInterval.value) {
    clearInterval(durationInterval.value)
  }

  if (streamResultUnsubscribe.value) {
    streamResultUnsubscribe.value()
  }

  localCurrentFrame.value = null
  streamingClient.disconnect()
})
</script>

<template>
  <div class="video-analyzer">
    <!-- Header -->
    <header class="analyzer-header">
      <div class="header-left">
        <button class="back-btn" @click="router.push('/')">
          <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
          </svg>
        </button>
        <div class="header-info">
          <h1 class="title">视频分析</h1>
          <span class="video-name" v-if="videoInfo">{{ videoInfo.original_filename }}</span>
        </div>
      </div>
      <div class="header-right">
        <div class="connection-status" :class="{ connected: isStreamConnected }">
          <span class="status-dot"></span>
          {{ isStreamConnected ? '已连接' : '未连接' }}
        </div>
        <div class="session-timer" v-if="isRunning">
          {{ formatTime(sessionDuration) }}
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <div class="analyzer-content">
      <!-- Video Panel -->
      <div class="video-panel hud-panel">
        <div class="hud-panel-header">
          <span class="hud-panel-title">视频画面</span>
          <span class="video-resolution" v-if="videoInfo">
            {{ videoInfo.width }}x{{ videoInfo.height }} @ {{ videoInfo.fps?.toFixed(0) }}fps
          </span>
        </div>

        <div class="video-container" ref="videoContainerRef">
          <video
            ref="videoRef"
            :src="videoSrc"
            crossorigin="anonymous"
            @loadedmetadata="onVideoLoaded"
            @timeupdate="onTimeUpdate"
            @ended="onVideoEnded"
            preload="metadata"
          ></video>

          <!-- Skeleton Overlay -->
          <SkeletonOverlay
            v-if="isVideoReady && currentPoses.length > 0"
            :poses="currentPoses"
            :width="actualVideoRect.width"
            :height="actualVideoRect.height"
            :offset-x="actualVideoRect.x"
            :offset-y="actualVideoRect.y"
            :show-angles="true"
          />

          <!-- Video Controls Overlay -->
          <div class="video-overlay" v-if="!isRunning && isVideoReady">
            <button class="play-btn" @click="startAnalysis">
              <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                <path d="M8 5v14l11-7z"/>
              </svg>
              <span>开始分析</span>
            </button>
          </div>
        </div>

        <!-- Playback Controls -->
        <div class="playback-controls" v-if="isVideoReady">
          <button class="control-btn" @click="togglePlay" :disabled="!isRunning">
            <svg v-if="isPlaying" viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
            </svg>
            <svg v-else viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M8 5v14l11-7z"/>
            </svg>
          </button>

          <div class="time-display">
            {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
          </div>

          <input
            type="range"
            class="seek-bar"
            :value="currentTime"
            :max="duration"
            step="0.1"
            @input="seekTo"
            :disabled="!isRunning"
          />

          <select
            class="speed-select"
            :value="playbackRate"
            @change="setPlaybackRate(parseFloat(($event.target as HTMLSelectElement).value))"
            :disabled="!isRunning"
          >
            <option :value="0.5">0.5x</option>
            <option :value="1.0">1.0x</option>
            <option :value="1.5">1.5x</option>
            <option :value="2.0">2.0x</option>
          </select>
        </div>
      </div>

      <!-- Side Panel -->
      <div class="side-panel">
        <!-- Score Panel -->
        <ScorePanel
          v-if="sessionStore.currentScores"
          :scores="sessionStore.currentScores"
        />

        <!-- Alert Panel -->
        <AlertPanel
          v-if="sessionStore.alerts.length > 0"
          :alerts="sessionStore.alerts"
        />

        <!-- Action Timeline -->
        <div class="hud-panel" v-if="actions.length > 0 || duration > 0">
          <div class="hud-panel-header">
            <span class="hud-panel-title">动作时间轴</span>
          </div>
          <ActionTimeline
            :actions="actions"
            :duration="duration"
            :current-time="currentTime"
            @seek="(time: number) => { if (videoRef) videoRef.currentTime = time }"
          />
        </div>

        <!-- Control Buttons -->
        <div class="control-panel" v-if="isRunning">
          <button
            class="hud-button hud-button--danger"
            @click="stopAnalysis(true)"
          >
            停止并生成报告
          </button>
        </div>
      </div>
    </div>

    <!-- Report Loading Modal -->
    <ReportLoadingModal
      ref="loadingModalRef"
      :visible="showReportLoading"
      @complete="onReportLoadingComplete"
    />
  </div>
</template>

<style scoped>
.video-analyzer {
  display: flex;
  flex-direction: column;
  height: 100vh;
  padding: var(--hud-spacing-md);
  gap: var(--hud-spacing-md);
}

.analyzer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  color: var(--hud-text-secondary);
  cursor: pointer;
  transition: var(--hud-transition);
}

.back-btn:hover {
  border-color: var(--hud-border);
  color: var(--hud-text-primary);
}

.header-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.title {
  font-size: 20px;
  color: var(--hud-border);
  margin: 0;
}

.video-name {
  font-size: 12px;
  color: var(--hud-text-muted);
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-lg);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-xs);
  font-size: 12px;
  color: var(--hud-text-muted);
}

.connection-status.connected {
  color: var(--hud-success);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--hud-text-muted);
}

.connection-status.connected .status-dot {
  background: var(--hud-success);
}

.session-timer {
  font-size: 18px;
  font-family: var(--font-mono);
  color: var(--hud-border);
}

.analyzer-content {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: var(--hud-spacing-md);
  flex: 1;
  min-height: 0;
}

.video-panel {
  display: flex;
  flex-direction: column;
}

.video-resolution {
  font-size: 11px;
  font-family: var(--font-mono);
  color: var(--hud-text-muted);
}

.video-container {
  flex: 1;
  position: relative;
  background: #000;
  border-radius: var(--hud-radius-sm);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-container video {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}

.video-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.5);
}

.play-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hud-spacing-sm);
  padding: var(--hud-spacing-lg);
  background: rgba(0, 212, 255, 0.1);
  border: 2px solid var(--hud-border);
  border-radius: var(--hud-radius-md);
  color: var(--hud-border);
  cursor: pointer;
  transition: var(--hud-transition);
}

.play-btn:hover {
  background: rgba(0, 212, 255, 0.2);
  box-shadow: var(--hud-glow);
}

.play-btn span {
  font-size: 14px;
}

.playback-controls {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
  padding: var(--hud-spacing-sm) 0;
  margin-top: var(--hud-spacing-sm);
}

.control-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  color: var(--hud-text-secondary);
  cursor: pointer;
  transition: var(--hud-transition);
}

.control-btn:hover:not(:disabled) {
  border-color: var(--hud-border);
  color: var(--hud-text-primary);
}

.control-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.time-display {
  font-size: 12px;
  font-family: var(--font-mono);
  color: var(--hud-text-secondary);
  min-width: 80px;
}

.seek-bar {
  flex: 1;
  height: 4px;
  -webkit-appearance: none;
  background: var(--hud-bg-light);
  border-radius: 2px;
  cursor: pointer;
}

.seek-bar::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 12px;
  height: 12px;
  background: var(--hud-border);
  border-radius: 50%;
  cursor: pointer;
}

.seek-bar:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.speed-select {
  padding: var(--hud-spacing-xs) var(--hud-spacing-sm);
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  color: var(--hud-text-secondary);
  font-size: 12px;
  cursor: pointer;
}

.speed-select:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.side-panel {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-md);
  overflow-y: auto;
  min-height: 0;
}

.control-panel {
  margin-top: var(--hud-spacing-md);
  flex-shrink: 0;
  padding-bottom: var(--hud-spacing-md);
}

.control-panel .hud-button {
  width: 100%;
  padding: var(--hud-spacing-md);
}

.hud-button--danger {
  background: rgba(255, 68, 68, 0.1);
  border-color: var(--hud-danger);
  color: var(--hud-danger);
}

.hud-button--danger:hover {
  background: rgba(255, 68, 68, 0.2);
}

@media (max-width: 1024px) {
  .analyzer-content {
    grid-template-columns: 1fr;
  }

  .side-panel {
    max-height: 300px;
  }
}
</style>
