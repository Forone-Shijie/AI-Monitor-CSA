<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useSessionStore } from '@/stores/session'
import { useReportStore } from '@/stores/report'
import SkeletonOverlay from '@/components/monitoring/SkeletonOverlay.vue'
import ActionTimeline from '@/components/monitoring/ActionTimeline.vue'
import ScorePanel from '@/components/monitoring/ScorePanel.vue'

const route = useRoute()
const sessionStore = useSessionStore()
const reportStore = useReportStore()

const selectedSessionId = ref<string>('')
const isPlaying = ref(false)
const currentFrameIndex = ref(0)
const playbackSpeed = ref(1)
const playInterval = ref<number | null>(null)

const sessions = computed(() =>
  sessionStore.sessions.filter(s => s.status === 'completed')
)

const playbackData = computed(() => reportStore.playbackData)
const timeline = computed(() => reportStore.timeline)
const summary = computed(() => reportStore.playbackSummary)

const currentFrame = computed(() => {
  if (!playbackData.value?.frames) return null
  return playbackData.value.frames[currentFrameIndex.value] || null
})

const currentTime = computed(() => {
  if (!currentFrame.value) return 0
  return currentFrame.value.timestamp
})

const totalDuration = computed(() =>
  playbackData.value?.duration || 0
)

const totalFrames = computed(() =>
  playbackData.value?.total_frames || 0
)

const progressPercent = computed(() => {
  if (totalFrames.value === 0) return 0
  return (currentFrameIndex.value / totalFrames.value) * 100
})

const currentScores = computed(() => {
  if (!reportStore.currentEvaluation?.scores) {
    return { pose: 0, action: 0, communication: 0, total: 0 }
  }
  const scores = reportStore.currentEvaluation.scores
  return {
    pose: scores.pose.score,
    action: scores.action.score,
    communication: scores.communication.score,
    total: scores.total
  }
})

async function loadSession(sessionId: string) {
  if (!sessionId) return

  selectedSessionId.value = sessionId
  stopPlayback()
  currentFrameIndex.value = 0

  try {
    await Promise.all([
      reportStore.fetchPlaybackData(sessionId),
      reportStore.fetchTimeline(sessionId),
      reportStore.fetchPlaybackSummary(sessionId),
      reportStore.fetchEvaluation(sessionId).catch(() => null)
    ])
  } catch (error) {
    console.error('Failed to load session data:', error)
  }
}

function togglePlayback() {
  if (isPlaying.value) {
    stopPlayback()
  } else {
    startPlayback()
  }
}

function startPlayback() {
  if (!playbackData.value?.frames) return

  isPlaying.value = true
  const fps = playbackData.value.fps || 30
  const interval = 1000 / (fps * playbackSpeed.value)

  playInterval.value = window.setInterval(() => {
    if (currentFrameIndex.value < totalFrames.value - 1) {
      currentFrameIndex.value++
    } else {
      stopPlayback()
    }
  }, interval)
}

function stopPlayback() {
  isPlaying.value = false
  if (playInterval.value) {
    clearInterval(playInterval.value)
    playInterval.value = null
  }
}

function seekTo(time: number) {
  if (!playbackData.value?.frames) return

  const frames = playbackData.value.frames
  let targetIndex = 0

  for (let i = 0; i < frames.length; i++) {
    const frame = frames[i]
    if (frame && frame.timestamp >= time) {
      targetIndex = i
      break
    }
    targetIndex = i
  }

  currentFrameIndex.value = targetIndex
}

function handleProgressClick(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const x = event.clientX - rect.left
  const percentage = x / rect.width
  const targetFrame = Math.floor(percentage * totalFrames.value)
  currentFrameIndex.value = Math.max(0, Math.min(targetFrame, totalFrames.value - 1))
}

function stepFrame(delta: number) {
  const newIndex = currentFrameIndex.value + delta
  currentFrameIndex.value = Math.max(0, Math.min(newIndex, totalFrames.value - 1))
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

watch(playbackSpeed, () => {
  if (isPlaying.value) {
    stopPlayback()
    startPlayback()
  }
})

onMounted(async () => {
  await sessionStore.fetchSessions()

  // Check if session ID is in route
  const sessionId = route.query.session as string
  if (sessionId) {
    await loadSession(sessionId)
  }
})
</script>

<template>
  <div class="playback-analysis">
    <!-- Header -->
    <header class="page-header">
      <h1>录像分析</h1>
      <div class="session-selector">
        <label>选择会话:</label>
        <select v-model="selectedSessionId" @change="loadSession(selectedSessionId)">
          <option value="">请选择...</option>
          <option
            v-for="session in sessions"
            :key="session.session_id"
            :value="session.session_id"
          >
            {{ session.trainee_name }} - {{ session.scenario_id || '自由训练' }}
          </option>
        </select>
      </div>
    </header>

    <!-- No Session Selected -->
    <div v-if="!selectedSessionId" class="no-selection">
      <div class="hud-panel">
        <div class="no-selection-icon">R</div>
        <h2>请选择训练会话</h2>
        <p>从上方下拉菜单选择已完成的训练会话进行回放分析</p>
      </div>
    </div>

    <!-- Playback Content -->
    <div v-else class="playback-content">
      <!-- Left: Video Playback -->
      <div class="video-section">
        <div class="hud-panel video-panel">
          <div class="hud-panel-header">
            <span class="hud-panel-title">视频回放</span>
            <span class="frame-info hud-number">
              帧 {{ currentFrameIndex + 1 }} / {{ totalFrames }}
            </span>
          </div>

          <div class="video-container">
            <div class="video-placeholder">
              <div class="video-corners">
                <div class="corner top-left"></div>
                <div class="corner top-right"></div>
                <div class="corner bottom-left"></div>
                <div class="corner bottom-right"></div>
              </div>
              <span class="placeholder-text">回放画面</span>
            </div>
            <SkeletonOverlay
              v-if="currentFrame?.pose"
              :poses="currentFrame.pose ? [currentFrame.pose] : null"
              :width="640"
              :height="360"
              :show-angles="true"
            />
          </div>

          <!-- Playback Controls -->
          <div class="playback-controls">
            <div class="control-row">
              <button class="control-btn" @click="stepFrame(-10)" title="后退10帧">
                &lt;&lt;
              </button>
              <button class="control-btn" @click="stepFrame(-1)" title="后退1帧">
                &lt;
              </button>
              <button
                class="control-btn play-btn"
                @click="togglePlayback"
              >
                {{ isPlaying ? '||' : '>' }}
              </button>
              <button class="control-btn" @click="stepFrame(1)" title="前进1帧">
                &gt;
              </button>
              <button class="control-btn" @click="stepFrame(10)" title="前进10帧">
                &gt;&gt;
              </button>
            </div>

            <div class="progress-bar" @click="handleProgressClick">
              <div class="progress-fill" :style="{ width: `${progressPercent}%` }"></div>
              <div class="progress-cursor" :style="{ left: `${progressPercent}%` }"></div>
            </div>

            <div class="time-display">
              <span class="current-time hud-number">{{ formatTime(currentTime) }}</span>
              <span class="time-separator">/</span>
              <span class="total-time hud-number">{{ formatTime(totalDuration) }}</span>

              <div class="speed-control">
                <label>速度:</label>
                <select v-model.number="playbackSpeed">
                  <option :value="0.25">0.25x</option>
                  <option :value="0.5">0.5x</option>
                  <option :value="1">1x</option>
                  <option :value="2">2x</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <!-- Timeline -->
        <div class="hud-panel timeline-panel">
          <ActionTimeline
            :events="timeline"
            :duration="totalDuration"
            :current-time="currentTime"
            @seek="seekTo"
          />
        </div>
      </div>

      <!-- Right: Analysis Info -->
      <div class="analysis-section">
        <!-- Summary -->
        <div class="hud-panel summary-panel" v-if="summary">
          <div class="hud-panel-header">
            <span class="hud-panel-title">会话摘要</span>
          </div>
          <div class="summary-grid">
            <div class="summary-item">
              <span class="summary-label">学员</span>
              <span class="summary-value">{{ summary.trainee_name }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">场景</span>
              <span class="summary-value">{{ summary.scenario_name || '自由训练' }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">时长</span>
              <span class="summary-value hud-number">{{ formatTime(summary.duration) }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">动作数</span>
              <span class="summary-value hud-number">{{ summary.action_count }}</span>
            </div>
            <div class="summary-item">
              <span class="summary-label">告警数</span>
              <span class="summary-value hud-number">{{ summary.alert_count }}</span>
            </div>
          </div>
        </div>

        <!-- Scores -->
        <div class="hud-panel scores-panel" v-if="reportStore.currentEvaluation">
          <div class="hud-panel-header">
            <span class="hud-panel-title">评估结果</span>
            <span class="grade-badge" :class="`grade--${reportStore.currentEvaluation.grade.toLowerCase()}`">
              {{ reportStore.currentEvaluation.grade }}
            </span>
          </div>
          <ScorePanel :scores="currentScores" />
        </div>

        <!-- Frame Details -->
        <div class="hud-panel frame-panel" v-if="currentFrame">
          <div class="hud-panel-header">
            <span class="hud-panel-title">当前帧数据</span>
          </div>
          <div class="frame-details">
            <div class="detail-item" v-if="currentFrame.pose">
              <span class="detail-label">姿态检测</span>
              <span class="detail-value" :class="currentFrame.pose.detected ? 'detected' : ''">
                {{ currentFrame.pose.detected ? '已检测' : '未检测到' }}
                <span v-if="currentFrame.pose.confidence" class="confidence">
                  ({{ (currentFrame.pose.confidence * 100).toFixed(0) }}%)
                </span>
              </span>
            </div>
            <div class="detail-item" v-if="currentFrame.action">
              <span class="detail-label">识别动作</span>
              <span class="detail-value action-name">
                {{ currentFrame.action.action_name }}
              </span>
            </div>
            <div class="detail-item" v-if="currentFrame.asr">
              <span class="detail-label">语音内容</span>
              <span class="detail-value asr-text">
                {{ currentFrame.asr.text }}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.playback-analysis {
  padding: var(--hud-spacing-lg);
  min-height: 100vh;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hud-spacing-lg);
}

.page-header h1 {
  color: var(--hud-border);
  font-size: 24px;
  margin: 0;
}

.session-selector {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
}

.session-selector label {
  font-size: 13px;
  color: var(--hud-text-secondary);
}

.session-selector select {
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  color: var(--hud-text-primary);
  font-size: 13px;
  min-width: 200px;
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60vh;
}

.no-selection .hud-panel {
  text-align: center;
  max-width: 400px;
}

.no-selection-icon {
  font-size: 48px;
  color: var(--hud-border);
  margin-bottom: var(--hud-spacing-md);
}

.no-selection h2 {
  color: var(--hud-text-primary);
  margin-bottom: var(--hud-spacing-sm);
}

.no-selection p {
  color: var(--hud-text-secondary);
}

.playback-content {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: var(--hud-spacing-lg);
}

.video-section {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-lg);
}

.video-container {
  position: relative;
  aspect-ratio: 16 / 9;
  background: var(--hud-bg-dark);
  border-radius: var(--hud-radius-sm);
  overflow: hidden;
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
}

.frame-info {
  font-size: 12px;
  color: var(--hud-text-secondary);
}

.playback-controls {
  margin-top: var(--hud-spacing-md);
}

.control-row {
  display: flex;
  justify-content: center;
  gap: var(--hud-spacing-sm);
  margin-bottom: var(--hud-spacing-md);
}

.control-btn {
  width: 40px;
  height: 40px;
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  color: var(--hud-text-primary);
  font-size: 14px;
  cursor: pointer;
  transition: var(--hud-transition);
}

.control-btn:hover {
  border-color: var(--hud-border);
  box-shadow: var(--hud-glow);
}

.play-btn {
  width: 50px;
  background: var(--hud-border);
  color: var(--hud-bg-dark);
  font-weight: 700;
}

.progress-bar {
  position: relative;
  height: 8px;
  background: var(--hud-bg-light);
  border-radius: 4px;
  cursor: pointer;
  margin-bottom: var(--hud-spacing-md);
}

.progress-fill {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(90deg, var(--hud-border) 0%, rgba(0, 212, 255, 0.5) 100%);
  border-radius: 4px;
  transition: width 0.1s linear;
}

.progress-cursor {
  position: absolute;
  top: 50%;
  width: 12px;
  height: 12px;
  background: var(--hud-border);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  box-shadow: 0 0 8px var(--hud-border);
}

.time-display {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--hud-spacing-sm);
  font-size: 14px;
}

.current-time {
  color: var(--hud-border);
}

.time-separator {
  color: var(--hud-text-muted);
}

.total-time {
  color: var(--hud-text-secondary);
}

.speed-control {
  margin-left: var(--hud-spacing-lg);
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-sm);
}

.speed-control label {
  font-size: 12px;
  color: var(--hud-text-muted);
}

.speed-control select {
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  padding: 2px 8px;
  color: var(--hud-text-primary);
  font-size: 12px;
}

.analysis-section {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-lg);
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--hud-spacing-sm);
}

.summary-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.summary-label {
  font-size: 11px;
  color: var(--hud-text-muted);
  text-transform: uppercase;
}

.summary-value {
  font-size: 14px;
  color: var(--hud-text-primary);
}

.grade-badge {
  font-size: 16px;
  font-weight: 700;
  padding: 2px 10px;
  border-radius: var(--hud-radius-sm);
}

.grade--a { color: var(--hud-success); background: rgba(0, 255, 136, 0.1); }
.grade--b { color: var(--hud-info); background: rgba(0, 212, 255, 0.1); }
.grade--c { color: var(--hud-warning); background: rgba(255, 204, 0, 0.1); }
.grade--d, .grade--f { color: var(--hud-danger); background: rgba(255, 68, 68, 0.1); }

.frame-details {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: var(--hud-spacing-sm);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
}

.detail-label {
  font-size: 11px;
  color: var(--hud-text-muted);
}

.detail-value {
  font-size: 13px;
  color: var(--hud-text-secondary);
}

.detail-value.detected {
  color: var(--hud-success);
}

.detail-value.action-name {
  color: var(--hud-border);
}

.confidence {
  font-size: 11px;
  color: var(--hud-text-muted);
}

@media (max-width: 1024px) {
  .playback-content {
    grid-template-columns: 1fr;
  }
}
</style>
