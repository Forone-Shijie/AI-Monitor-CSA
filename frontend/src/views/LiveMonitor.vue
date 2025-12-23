<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useConfigStore } from '@/stores/config'
import { useMediaStore } from '@/stores/media'
import ScorePanel from '@/components/monitoring/ScorePanel.vue'
import AlertPanel from '@/components/monitoring/AlertPanel.vue'
import SkeletonOverlay from '@/components/monitoring/SkeletonOverlay.vue'
import ActionTimeline from '@/components/monitoring/ActionTimeline.vue'
import { streamingClient } from '@/services/websocket'
import { captureVideoFrame } from '@/services/mediaDevices'
import type { PoseData, ActionData } from '@/types/api'

const router = useRouter()
const sessionStore = useSessionStore()
const mediaStore = useMediaStore()
// configStore is used for future video source configuration
void useConfigStore()

const videoRef = ref<HTMLVideoElement | null>(null)
const videoContainerRef = ref<HTMLDivElement | null>(null)
const videoWidth = ref(640)
const videoHeight = ref(480)
const sessionDuration = ref(0)
const durationInterval = ref<number | null>(null)
const isVideoReady = ref(false)
const frameCapturerInterval = ref<number | null>(null)
const targetFps = ref(10) // Send frames at 10 FPS to backend
const streamResultUnsubscribe = ref<(() => void) | null>(null)

const hasSession = computed(() => sessionStore.hasActiveSession)
const isRunning = computed(() => sessionStore.isRunning)
const isStreamConnected = ref(false)

// Track streaming connection status
streamingClient.onConnect(() => { isStreamConnected.value = true })
streamingClient.onDisconnect(() => { isStreamConnected.value = false })

const currentPose = computed<PoseData | null>(() =>
  sessionStore.currentFrame?.pose || null
)

const actions = computed<ActionData[]>(() => {
  const actionList: ActionData[] = []
  for (const frame of sessionStore.frameHistory) {
    if (frame.action) {
      actionList.push(frame.action)
    }
  }
  return actionList
})

const asrText = computed(() => {
  if (!sessionStore.currentFrame?.asr) return ''
  return sessionStore.currentFrame.asr.text
})

const braceStatus = computed(() => {
  if (!sessionStore.currentFrame?.brace) return null
  return sessionStore.currentFrame.brace
})

async function startVideoStream() {
  // Start video capture from browser
  const success = await mediaStore.startVideo()
  if (success && mediaStore.videoStream && videoRef.value) {
    videoRef.value.srcObject = mediaStore.videoStream
    videoRef.value.onloadedmetadata = () => {
      isVideoReady.value = true
      videoRef.value?.play()
    }
  }
}

function stopVideoStream() {
  if (videoRef.value) {
    videoRef.value.srcObject = null
  }
  mediaStore.stopVideo()
  isVideoReady.value = false
}

function startFrameCapturer() {
  if (frameCapturerInterval.value) return

  const interval = 1000 / targetFps.value
  frameCapturerInterval.value = window.setInterval(async () => {
    if (!videoRef.value || !isVideoReady.value || !streamingClient.isConnected) return

    // Capture frame from video element
    const blob = await captureVideoFrame(videoRef.value, 'image/jpeg', 0.7)
    if (blob) {
      // Send frame to backend via streaming WebSocket
      streamingClient.sendFrame(blob)
    }
  }, interval)
}

function stopFrameCapturer() {
  if (frameCapturerInterval.value) {
    window.clearInterval(frameCapturerInterval.value)
    frameCapturerInterval.value = null
  }
}

async function startMonitoring() {
  if (!sessionStore.activeSession) return

  try {
    // Start video stream first
    await startVideoStream()

    // Then start monitoring session (this connects WebSocket for status updates)
    await sessionStore.startSession(sessionStore.activeSession.session_id)
    startDurationTimer()

    // Connect streaming WebSocket for sending frames
    await streamingClient.connect(sessionStore.activeSession.session_id)

    // Register handler to receive pose detection results
    streamResultUnsubscribe.value = streamingClient.onResult((result) => {
      // Update currentFrame with pose detection results from backend
      sessionStore.currentFrame = {
        frame_number: result.frame_number as number,
        timestamp: result.timestamp as number,
        pose: result.pose as PoseData | undefined,
        alerts: []
      }
    })

    // Start sending frames to backend
    startFrameCapturer()
  } catch (error) {
    console.error('Failed to start monitoring:', error)
    stopVideoStream()
    stopFrameCapturer()
    streamingClient.disconnect()
  }
}

function cleanupStreamHandler() {
  if (streamResultUnsubscribe.value) {
    streamResultUnsubscribe.value()
    streamResultUnsubscribe.value = null
  }
}

async function stopMonitoring() {
  if (!sessionStore.activeSession) return

  try {
    stopFrameCapturer()
    cleanupStreamHandler()
    streamingClient.disconnect()
    stopVideoStream()
    await sessionStore.stopSession(sessionStore.activeSession.session_id, true)
    stopDurationTimer()
    router.push('/reports')
  } catch (error) {
    console.error('Failed to stop monitoring:', error)
  }
}

async function pauseMonitoring() {
  if (!sessionStore.activeSession) return

  try {
    stopFrameCapturer()
    cleanupStreamHandler()
    streamingClient.disconnect()
    stopVideoStream()
    await sessionStore.pauseSession(sessionStore.activeSession.session_id)
    stopDurationTimer()
  } catch (error) {
    console.error('Failed to pause monitoring:', error)
  }
}

function startDurationTimer() {
  if (durationInterval.value) return
  durationInterval.value = window.setInterval(() => {
    sessionDuration.value++
  }, 1000)
}

function stopDurationTimer() {
  if (durationInterval.value) {
    clearInterval(durationInterval.value)
    durationInterval.value = null
  }
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function handleResize() {
  if (videoContainerRef.value) {
    const rect = videoContainerRef.value.getBoundingClientRect()
    videoWidth.value = rect.width
    videoHeight.value = (rect.width * 9) / 16
  }
}

watch(isRunning, (running) => {
  if (running) {
    startDurationTimer()
  } else {
    stopDurationTimer()
  }
})

onMounted(() => {
  handleResize()
  window.addEventListener('resize', handleResize)

  if (isRunning.value) {
    startDurationTimer()
  }
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  stopDurationTimer()
  stopFrameCapturer()
  cleanupStreamHandler()
  streamingClient.disconnect()
  stopVideoStream()
})
</script>

<template>
  <div class="live-monitor">
    <!-- Header -->
    <header class="page-header">
      <div class="header-left">
        <h1>实时监控</h1>
        <span
          v-if="hasSession"
          class="session-badge"
          :class="{ 'session-badge--running': isRunning }"
        >
          {{ sessionStore.activeSession?.trainee_name }}
        </span>
      </div>
      <div class="header-right">
        <div class="duration-display" v-if="hasSession">
          <span class="duration-label">时长</span>
          <span class="duration-value hud-number">{{ formatDuration(sessionDuration) }}</span>
        </div>
        <div class="connection-status" :class="{ 'connected': isStreamConnected }">
          <span class="status-dot"></span>
          {{ isStreamConnected ? '已连接' : '未连接' }}
        </div>
      </div>
    </header>

    <!-- No Session State -->
    <div v-if="!hasSession" class="no-session">
      <div class="hud-panel no-session-panel">
        <div class="no-session-icon">M</div>
        <h2>无活动训练</h2>
        <p>请在仪表盘创建新的训练会话</p>
        <router-link to="/" class="hud-button hud-button--primary">
          返回仪表盘
        </router-link>
      </div>
    </div>

    <!-- Monitor Content -->
    <div v-else class="monitor-content">
      <!-- Left: Video & Skeleton -->
      <div class="video-section">
        <div class="hud-panel video-panel">
          <div class="hud-panel-header">
            <span class="hud-panel-title">视频画面</span>
            <span class="fps-display hud-number">30 FPS</span>
          </div>
          <div ref="videoContainerRef" class="video-container">
            <!-- Video element for browser camera -->
            <video
              ref="videoRef"
              class="video-element"
              autoplay
              playsinline
              muted
              :class="{ 'video-hidden': !isVideoReady }"
            ></video>

            <!-- Placeholder when video not ready -->
            <div class="video-placeholder" v-if="!isVideoReady">
              <div class="video-grid">
                <div class="grid-line horizontal" style="top: 33%"></div>
                <div class="grid-line horizontal" style="top: 66%"></div>
                <div class="grid-line vertical" style="left: 33%"></div>
                <div class="grid-line vertical" style="left: 66%"></div>
              </div>
              <div class="video-crosshair">
                <div class="crosshair-h"></div>
                <div class="crosshair-v"></div>
              </div>
              <div class="video-corners">
                <div class="corner top-left"></div>
                <div class="corner top-right"></div>
                <div class="corner bottom-left"></div>
                <div class="corner bottom-right"></div>
              </div>
              <span class="placeholder-text">
                {{ mediaStore.cameraPermission === 'denied' ? '摄像头权限被拒绝' : '等待视频流...' }}
              </span>
            </div>

            <!-- Video overlay corners (always visible) -->
            <div class="video-overlay" v-if="isVideoReady">
              <div class="video-corners">
                <div class="corner top-left"></div>
                <div class="corner top-right"></div>
                <div class="corner bottom-left"></div>
                <div class="corner bottom-right"></div>
              </div>
            </div>

            <!-- Skeleton Overlay -->
            <SkeletonOverlay
              v-if="currentPose"
              :pose-data="currentPose"
              :width="videoWidth"
              :height="videoHeight"
              :show-angles="true"
            />

            <!-- Debug Info Overlay -->
            <div class="debug-overlay" v-if="isRunning">
              <div class="debug-item">
                连接: {{ isStreamConnected ? '✓' : '✗' }}
              </div>
              <div class="debug-item" v-if="sessionStore.currentFrame">
                帧#: {{ sessionStore.currentFrame.frame_number }}
              </div>
              <div class="debug-item" v-if="sessionStore.currentFrame?.pose">
                检测: {{ sessionStore.currentFrame.pose.detected ? '✓' : '✗' }}
              </div>
              <div class="debug-item" v-if="sessionStore.currentFrame?.pose">
                置信度: {{ (sessionStore.currentFrame.pose.confidence * 100).toFixed(1) }}%
              </div>
              <div class="debug-item" v-if="sessionStore.currentFrame?.pose?.keypoints">
                关键点: {{ sessionStore.currentFrame.pose.keypoints.length }}
              </div>
            </div>
          </div>
        </div>

        <!-- Brace Position Status -->
        <div class="hud-panel brace-panel" v-if="braceStatus">
          <div class="hud-panel-header">
            <span class="hud-panel-title">防冲击姿势</span>
            <span
              class="hud-status"
              :class="braceStatus.is_valid ? 'hud-status--success' : 'hud-status--warning'"
            >
              <span class="hud-status-dot"></span>
              {{ braceStatus.is_valid ? '合规' : '调整中' }}
            </span>
          </div>
          <div class="brace-parts">
            <div
              v-for="(part, key) in braceStatus.body_parts"
              :key="key"
              class="brace-part"
              :class="{ 'brace-part--ok': part.is_compliant }"
            >
              <span class="part-name">{{ part.name }}</span>
              <span class="part-score hud-number">{{ Math.round(part.score) }}</span>
            </div>
          </div>
          <div class="hold-duration">
            保持时长: <span class="hud-number">{{ braceStatus.hold_duration.toFixed(1) }}s</span>
          </div>
        </div>

        <!-- ASR Display -->
        <div class="hud-panel asr-panel">
          <div class="hud-panel-header">
            <span class="hud-panel-title">语音识别</span>
          </div>
          <div class="asr-content">
            <p v-if="asrText" class="asr-text">{{ asrText }}</p>
            <p v-else class="asr-placeholder">等待语音输入...</p>
          </div>
        </div>
      </div>

      <!-- Right: Scores & Controls -->
      <div class="control-section">
        <!-- Score Panel -->
        <div class="hud-panel score-panel-wrapper">
          <div class="hud-panel-header">
            <span class="hud-panel-title">实时评分</span>
          </div>
          <ScorePanel :scores="sessionStore.currentScores" />
        </div>

        <!-- Action Timeline -->
        <div class="hud-panel timeline-panel">
          <ActionTimeline
            :actions="actions"
            :duration="sessionDuration || 60"
            :current-time="sessionDuration"
          />
        </div>

        <!-- Alerts -->
        <div class="hud-panel alerts-panel">
          <AlertPanel
            :alerts="sessionStore.recentAlerts"
            @clear="sessionStore.clearAlerts"
          />
        </div>

        <!-- Control Buttons -->
        <div class="control-buttons">
          <button
            v-if="!isRunning"
            class="hud-button hud-button--primary control-btn"
            @click="startMonitoring"
          >
            开始监测
          </button>
          <template v-else>
            <button
              class="hud-button control-btn"
              @click="pauseMonitoring"
            >
              暂停
            </button>
            <button
              class="hud-button control-btn stop-btn"
              @click="stopMonitoring"
            >
              结束并生成报告
            </button>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.live-monitor {
  padding: var(--hud-spacing-lg);
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hud-spacing-lg);
}

.header-left {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
}

.page-header h1 {
  color: var(--hud-border);
  font-size: 24px;
  margin: 0;
}

.session-badge {
  padding: var(--hud-spacing-xs) var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  font-size: 12px;
  color: var(--hud-text-secondary);
}

.session-badge--running {
  border-color: var(--hud-success);
  color: var(--hud-success);
  animation: glow 2s infinite;
}

.header-right {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-lg);
}

.duration-display {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.duration-label {
  font-size: 10px;
  color: var(--hud-text-muted);
  text-transform: uppercase;
}

.duration-value {
  font-size: 24px;
  color: var(--hud-border);
}

.connection-status {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-sm);
  font-size: 12px;
  color: var(--hud-text-muted);
}

.connection-status .status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--hud-danger);
}

.connection-status.connected .status-dot {
  background: var(--hud-success);
  box-shadow: 0 0 8px var(--hud-success);
}

.no-session {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.no-session-panel {
  text-align: center;
  max-width: 400px;
}

.no-session-icon {
  font-size: 48px;
  color: var(--hud-border);
  margin-bottom: var(--hud-spacing-md);
}

.no-session-panel h2 {
  color: var(--hud-text-primary);
  margin-bottom: var(--hud-spacing-sm);
}

.no-session-panel p {
  color: var(--hud-text-secondary);
  margin-bottom: var(--hud-spacing-lg);
}

.monitor-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--hud-spacing-lg);
}

.video-section {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-lg);
}

.video-panel .hud-panel-header {
  display: flex;
  justify-content: space-between;
}

.fps-display {
  font-size: 12px;
  color: var(--hud-success);
}

.video-container {
  position: relative;
  aspect-ratio: 16 / 9;
  background: var(--hud-bg-dark);
  border-radius: var(--hud-radius-sm);
  overflow: hidden;
}

.video-element {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 1;
}

.video-element.video-hidden {
  opacity: 0;
}

.video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
  pointer-events: none;
}

.video-placeholder {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.video-grid {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
}

.grid-line {
  position: absolute;
  background: rgba(0, 212, 255, 0.1);
}

.grid-line.horizontal {
  left: 0;
  right: 0;
  height: 1px;
}

.grid-line.vertical {
  top: 0;
  bottom: 0;
  width: 1px;
}

.video-crosshair {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
}

.crosshair-h,
.crosshair-v {
  position: absolute;
  background: rgba(0, 212, 255, 0.5);
}

.crosshair-h {
  width: 20px;
  height: 1px;
  left: -10px;
}

.crosshair-v {
  width: 1px;
  height: 20px;
  top: -10px;
}

.video-corners .corner {
  position: absolute;
  width: 20px;
  height: 20px;
  border-color: var(--hud-border);
  border-style: solid;
}

.corner.top-left { top: 10px; left: 10px; border-width: 2px 0 0 2px; }
.corner.top-right { top: 10px; right: 10px; border-width: 2px 2px 0 0; }
.corner.bottom-left { bottom: 10px; left: 10px; border-width: 0 0 2px 2px; }
.corner.bottom-right { bottom: 10px; right: 10px; border-width: 0 2px 2px 0; }

.placeholder-text {
  color: var(--hud-text-muted);
  font-size: 14px;
  z-index: 1;
}

.brace-parts {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--hud-spacing-sm);
  margin-bottom: var(--hud-spacing-md);
}

.brace-part {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--hud-spacing-sm);
  background: rgba(255, 204, 0, 0.1);
  border-left: 3px solid var(--hud-warning);
  border-radius: var(--hud-radius-sm);
}

.brace-part--ok {
  background: rgba(0, 255, 136, 0.1);
  border-color: var(--hud-success);
}

.part-name {
  font-size: 12px;
  color: var(--hud-text-secondary);
}

.part-score {
  font-size: 16px;
  color: var(--hud-border);
}

.hold-duration {
  font-size: 13px;
  color: var(--hud-text-secondary);
  text-align: center;
}

.asr-content {
  min-height: 60px;
}

.asr-text {
  font-size: 16px;
  color: var(--hud-text-primary);
  line-height: 1.5;
}

.asr-placeholder {
  color: var(--hud-text-muted);
  font-style: italic;
}

.control-section {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-lg);
}

.score-panel-wrapper,
.timeline-panel,
.alerts-panel {
  flex-shrink: 0;
}

.control-buttons {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-md);
  margin-top: auto;
}

.control-btn {
  width: 100%;
  padding: var(--hud-spacing-md);
  font-size: 14px;
}

.stop-btn {
  border-color: var(--hud-danger);
  color: var(--hud-danger);
}

.stop-btn:hover {
  background: rgba(255, 68, 68, 0.1);
}

@media (max-width: 1024px) {
  .monitor-content {
    grid-template-columns: 1fr;
  }
}

.debug-overlay {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(0, 0, 0, 0.7);
  padding: 8px 12px;
  border-radius: 4px;
  z-index: 10;
  font-size: 11px;
  font-family: monospace;
}

.debug-item {
  color: var(--hud-border);
  margin-bottom: 2px;
}

.debug-item:last-child {
  margin-bottom: 0;
}
</style>
