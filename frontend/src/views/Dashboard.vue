<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useConfigStore } from '@/stores/config'
import { useSessionStore } from '@/stores/session'
import { useReportStore } from '@/stores/report'
import { useMediaStore } from '@/stores/media'
import ScorePanel from '@/components/monitoring/ScorePanel.vue'
import type { SessionInfo } from '@/types/api'

const router = useRouter()
const configStore = useConfigStore()
const sessionStore = useSessionStore()
const reportStore = useReportStore()
const mediaStore = useMediaStore()

const isLoading = ref(true)
const showNewSession = ref(false)
const showEditSession = ref(false)
const newSession = ref({
  trainee_id: '',
  trainee_name: '',
  scenario_id: '',
  camera_id: '' as string,
  audio_device_id: '' as string
})
const editSession = ref({
  session_id: '',
  trainee_id: '',
  trainee_name: '',
  scenario_id: '',
  camera_id: '' as string,
  audio_device_id: '' as string
})

const systemModules = computed(() => [
  {
    name: '姿态检测',
    key: 'pose_detection',
    status: configStore.isBackendOnline ? 'ready' : 'offline'
  },
  {
    name: '语音识别',
    key: 'asr',
    status: configStore.isBackendOnline ? 'ready' : 'offline'
  },
  {
    name: 'SOP分析',
    key: 'sop_analysis',
    status: configStore.isBackendOnline ? 'ready' : 'offline'
  },
  {
    name: '评估引擎',
    key: 'evaluation',
    status: configStore.isBackendOnline ? 'ready' : 'offline'
  }
])

const recentReports = computed(() => (reportStore.reports ?? []).slice(0, 5))

const stats = computed(() => ({
  totalSessions: (sessionStore.sessions ?? []).length,
  totalReports: reportStore.totalReports,
  averageScore: reportStore.averageScore
}))

const quickActions = [
  { path: '/live', icon: 'M', label: '开始监控', color: 'var(--hud-success)' },
  { path: '/playback', icon: 'R', label: '录像分析', color: 'var(--hud-info)' },
  { path: '/reports', icon: 'A', label: '查看报告', color: 'var(--hud-warning)' }
]

async function loadData() {
  isLoading.value = true
  try {
    await Promise.all([
      sessionStore.fetchSessions(),
      reportStore.fetchReports(),
      initializeMediaDevices()
    ])
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  } finally {
    isLoading.value = false
  }
}

async function initializeMediaDevices() {
  // Initialize media store - this will check permissions and get device list
  await mediaStore.initialize()

  // Set defaults if devices available
  const firstCamera = mediaStore.cameras[0]
  const firstMic = mediaStore.microphones[0]
  if (firstCamera && !newSession.value.camera_id) {
    newSession.value.camera_id = firstCamera.deviceId
  }
  if (firstMic && !newSession.value.audio_device_id) {
    newSession.value.audio_device_id = firstMic.deviceId
  }
}

async function requestMediaPermissions() {
  const success = await mediaStore.requestPermissions()
  if (success) {
    // Update default selections
    const firstCamera = mediaStore.cameras[0]
    const firstMic = mediaStore.microphones[0]
    if (firstCamera && !newSession.value.camera_id) {
      newSession.value.camera_id = firstCamera.deviceId
    }
    if (firstMic && !newSession.value.audio_device_id) {
      newSession.value.audio_device_id = firstMic.deviceId
    }
  }
}

async function createNewSession() {
  if (!newSession.value.trainee_id || !newSession.value.trainee_name) {
    return
  }

  try {
    // Store selected browser devices in media store for later use in LiveMonitor
    if (newSession.value.camera_id) {
      mediaStore.selectCamera(newSession.value.camera_id)
    }
    if (newSession.value.audio_device_id) {
      mediaStore.selectMicrophone(newSession.value.audio_device_id)
    }

    // Create session - camera_id 0 tells backend to use browser-based video
    const session = await sessionStore.createSession({
      trainee_id: newSession.value.trainee_id,
      trainee_name: newSession.value.trainee_name,
      scenario_id: newSession.value.scenario_id || undefined,
      camera_id: 0, // Use browser-based video
      audio_device_id: undefined
    })

    if (session) {
      showNewSession.value = false
      router.push('/live')
    }
  } catch (error) {
    console.error('Failed to create session:', error)
  }
}

function getStatusClass(status: string): string {
  switch (status) {
    case 'ready': return 'status--success'
    case 'offline': return 'status--danger'
    default: return 'status--warning'
  }
}

function getStatusText(status: string): string {
  switch (status) {
    case 'ready': return '就绪'
    case 'offline': return '离线'
    default: return '检测中'
  }
}

function getGradeClass(grade: string): string {
  switch (grade) {
    case 'A': return 'grade--a'
    case 'B': return 'grade--b'
    case 'C': return 'grade--c'
    default: return 'grade--d'
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getSessionStatusClass(status: string): string {
  switch (status) {
    case 'running': return 'session-status--running'
    case 'completed': return 'session-status--completed'
    case 'cancelled': return 'session-status--cancelled'
    case 'paused': return 'session-status--paused'
    default: return 'session-status--created'
  }
}

function getSessionStatusText(status: string): string {
  switch (status) {
    case 'running': return '运行中'
    case 'completed': return '已完成'
    case 'cancelled': return '已取消'
    case 'paused': return '已暂停'
    case 'created': return '已创建'
    default: return status
  }
}

async function handleDeleteSession(sessionId: string, traineeName: string) {
  if (confirm(`确定要删除学员"${traineeName}"的训练会话吗？此操作不可撤销。`)) {
    try {
      await sessionStore.deleteSession(sessionId)
    } catch (error) {
      console.error('Failed to delete session:', error)
    }
  }
}

function openEditSession(session: SessionInfo) {
  editSession.value = {
    session_id: session.session_id,
    trainee_id: session.trainee_id,
    trainee_name: session.trainee_name,
    scenario_id: session.scenario_id || '',
    camera_id: '',
    audio_device_id: ''
  }
  showEditSession.value = true
}

async function saveEditSession() {
  if (!editSession.value.trainee_id || !editSession.value.trainee_name) {
    return
  }

  try {
    // Store selected browser devices in media store for later use
    if (editSession.value.camera_id) {
      mediaStore.selectCamera(editSession.value.camera_id)
    }
    if (editSession.value.audio_device_id) {
      mediaStore.selectMicrophone(editSession.value.audio_device_id)
    }

    // Update session - only update trainee info and scenario
    await sessionStore.updateSession(editSession.value.session_id, {
      trainee_id: editSession.value.trainee_id,
      trainee_name: editSession.value.trainee_name,
      scenario_id: editSession.value.scenario_id || undefined
    })
    showEditSession.value = false
  } catch (error) {
    console.error('Failed to update session:', error)
  }
}

function canEditSession(status: string): boolean {
  return status !== 'running'
}

onMounted(loadData)
</script>

<template>
  <div class="dashboard">
    <!-- Header -->
    <header class="dashboard-header">
      <div class="header-content">
        <h1 class="title">乘务监测系统</h1>
        <p class="subtitle">客舱乘务员姿态与操作规范监测系统</p>
      </div>
      <button class="hud-button hud-button--primary" @click="showNewSession = true">
        + 新建训练
      </button>
    </header>

    <!-- Stats Row -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value hud-number">{{ stats.totalSessions }}</span>
        <span class="stat-label">训练会话</span>
      </div>
      <div class="stat-card">
        <span class="stat-value hud-number">{{ stats.totalReports }}</span>
        <span class="stat-label">评估报告</span>
      </div>
      <div class="stat-card">
        <span class="stat-value hud-number">{{ stats.averageScore }}</span>
        <span class="stat-label">平均分数</span>
      </div>
    </div>

    <!-- Main Grid -->
    <div class="dashboard-grid">
      <!-- System Status Panel -->
      <div class="hud-panel status-panel">
        <div class="hud-panel-header">
          <span class="hud-panel-title">系统状态</span>
          <span
            class="hud-status"
            :class="configStore.isBackendOnline ? 'hud-status--success' : 'hud-status--danger'"
          >
            <span class="hud-status-dot"></span>
            {{ configStore.isBackendOnline ? '系统在线' : '系统离线' }}
          </span>
        </div>
        <div class="module-list">
          <div
            v-for="module in systemModules"
            :key="module.key"
            class="module-item"
          >
            <span class="module-name">{{ module.name }}</span>
            <span class="module-status" :class="getStatusClass(module.status)">
              {{ getStatusText(module.status) }}
            </span>
          </div>
        </div>
      </div>

      <!-- Quick Actions Panel -->
      <div class="hud-panel actions-panel">
        <div class="hud-panel-header">
          <span class="hud-panel-title">快速操作</span>
        </div>
        <div class="actions-grid">
          <router-link
            v-for="action in quickActions"
            :key="action.path"
            :to="action.path"
            class="action-card"
          >
            <div class="action-icon" :style="{ color: action.color }">{{ action.icon }}</div>
            <div class="action-label">{{ action.label }}</div>
          </router-link>
        </div>
      </div>

      <!-- Recent Reports Panel -->
      <div class="hud-panel reports-panel">
        <div class="hud-panel-header">
          <span class="hud-panel-title">最近报告</span>
          <router-link to="/reports" class="view-all">查看全部</router-link>
        </div>
        <div class="report-list" v-if="recentReports.length > 0">
          <div
            v-for="report in recentReports"
            :key="report.report_id"
            class="report-item"
          >
            <div class="report-info">
              <span class="report-trainee">{{ report.trainee_name }}</span>
              <span class="report-scenario">{{ report.scenario_name }}</span>
            </div>
            <div class="report-score">
              <span class="score-value hud-number">{{ report.total_score }}</span>
              <span class="score-grade" :class="getGradeClass(report.grade)">{{ report.grade }}</span>
            </div>
            <span class="report-date">{{ formatDate(report.generated_at) }}</span>
          </div>
        </div>
        <div v-else class="report-empty">
          暂无评估报告
        </div>
      </div>

      <!-- Session List Panel -->
      <div class="hud-panel sessions-panel">
        <div class="hud-panel-header">
          <span class="hud-panel-title">训练会话</span>
          <span class="session-count">共 {{ sessionStore.sessions?.length ?? 0 }} 个</span>
        </div>
        <div class="session-list" v-if="(sessionStore.sessions ?? []).length > 0">
          <div
            v-for="session in sessionStore.sessions"
            :key="session.session_id"
            class="session-item"
          >
            <div class="session-item-info">
              <span class="session-trainee">{{ session.trainee_name }}</span>
              <span class="session-id">{{ session.trainee_id }}</span>
            </div>
            <span class="session-status" :class="getSessionStatusClass(session.status)">
              {{ getSessionStatusText(session.status) }}
            </span>
            <span class="session-date">{{ formatDate(session.created_at) }}</span>
            <div class="session-actions-btns">
              <button
                class="edit-btn"
                @click="openEditSession(session)"
                :disabled="!canEditSession(session.status)"
                :title="canEditSession(session.status) ? '编辑会话' : '运行中的会话无法编辑'"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" class="action-icon">
                  <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                </svg>
              </button>
              <button
                class="delete-btn"
                @click="handleDeleteSession(session.session_id, session.trainee_name)"
                :disabled="session.status === 'running'"
                :title="session.status === 'running' ? '运行中的会话无法删除' : '删除会话'"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" class="action-icon">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
              </button>
            </div>
          </div>
        </div>
        <div v-else class="session-empty">
          暂无训练会话
        </div>
      </div>

      <!-- Active Session Panel -->
      <div class="hud-panel session-panel" v-if="sessionStore.hasActiveSession">
        <div class="hud-panel-header">
          <span class="hud-panel-title">当前训练</span>
          <span class="hud-status hud-status--success">
            <span class="hud-status-dot"></span>
            进行中
          </span>
        </div>
        <div class="session-info">
          <p><strong>学员:</strong> {{ sessionStore.activeSession?.trainee_name }}</p>
          <p><strong>场景:</strong> {{ sessionStore.activeSession?.scenario_id || '未指定' }}</p>
        </div>
        <ScorePanel
          v-if="sessionStore.currentScores"
          :scores="sessionStore.currentScores"
          :compact="true"
        />
        <div class="session-actions">
          <router-link to="/live" class="hud-button hud-button--primary">
            进入监控
          </router-link>
        </div>
      </div>
    </div>

    <!-- New Session Modal -->
    <Teleport to="body">
      <div v-if="showNewSession" class="modal-overlay" @click.self="showNewSession = false">
        <div class="modal hud-panel">
          <div class="hud-panel-header">
            <span class="hud-panel-title">新建训练会话</span>
            <button class="close-btn" @click="showNewSession = false">x</button>
          </div>
          <form class="modal-form" @submit.prevent="createNewSession">
            <div class="form-group">
              <label>学员编号</label>
              <input
                v-model="newSession.trainee_id"
                type="text"
                placeholder="例如: T001"
                required
              />
            </div>
            <div class="form-group">
              <label>学员姓名</label>
              <input
                v-model="newSession.trainee_name"
                type="text"
                placeholder="例如: 张三"
                required
              />
            </div>
            <div class="form-group">
              <label>训练场景</label>
              <select v-model="newSession.scenario_id">
                <option value="">自由训练</option>
                <option
                  v-for="scenario in configStore.scenarioOptions"
                  :key="scenario.value"
                  :value="scenario.value"
                >
                  {{ scenario.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>摄像头</label>
              <div v-if="!mediaStore.isPermissionGranted" class="permission-request">
                <span class="form-hint form-hint--info">需要授权访问摄像头和麦克风</span>
                <button type="button" class="hud-button hud-button--small" @click="requestMediaPermissions">
                  请求权限
                </button>
              </div>
              <select v-else v-model="newSession.camera_id">
                <option value="" disabled>{{ mediaStore.cameras.length === 0 ? '未检测到摄像头' : '请选择摄像头' }}</option>
                <option
                  v-for="camera in mediaStore.cameras"
                  :key="camera.deviceId"
                  :value="camera.deviceId"
                >
                  {{ camera.label }}
                </option>
              </select>
              <span v-if="mediaStore.isPermissionGranted && mediaStore.cameras.length === 0" class="form-hint form-hint--warning">
                未检测到可用摄像头，将使用模拟数据
              </span>
            </div>
            <div class="form-group">
              <label>音频设备</label>
              <select v-model="newSession.audio_device_id" :disabled="!mediaStore.isPermissionGranted">
                <option value="" disabled>{{ mediaStore.microphones.length === 0 ? '未检测到音频设备' : '请选择音频设备' }}</option>
                <option
                  v-for="mic in mediaStore.microphones"
                  :key="mic.deviceId"
                  :value="mic.deviceId"
                >
                  {{ mic.label }}
                </option>
              </select>
              <span v-if="mediaStore.isPermissionGranted && mediaStore.microphones.length === 0" class="form-hint form-hint--warning">
                未检测到可用音频设备
              </span>
            </div>
            <div class="form-actions">
              <button type="button" class="hud-button" @click="showNewSession = false">
                取消
              </button>
              <button type="submit" class="hud-button hud-button--primary">
                创建并开始
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Edit Session Modal -->
    <Teleport to="body">
      <div v-if="showEditSession" class="modal-overlay" @click.self="showEditSession = false">
        <div class="modal hud-panel">
          <div class="hud-panel-header">
            <span class="hud-panel-title">编辑训练会话</span>
            <button class="close-btn" @click="showEditSession = false">x</button>
          </div>
          <form class="modal-form" @submit.prevent="saveEditSession">
            <div class="form-group">
              <label>学员编号</label>
              <input
                v-model="editSession.trainee_id"
                type="text"
                placeholder="例如: T001"
                required
              />
            </div>
            <div class="form-group">
              <label>学员姓名</label>
              <input
                v-model="editSession.trainee_name"
                type="text"
                placeholder="例如: 张三"
                required
              />
            </div>
            <div class="form-group">
              <label>训练场景</label>
              <select v-model="editSession.scenario_id">
                <option value="">自由训练</option>
                <option
                  v-for="scenario in configStore.scenarioOptions"
                  :key="scenario.value"
                  :value="scenario.value"
                >
                  {{ scenario.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>摄像头</label>
              <div v-if="!mediaStore.isPermissionGranted" class="permission-request">
                <span class="form-hint form-hint--info">需要授权访问摄像头和麦克风</span>
                <button type="button" class="hud-button hud-button--small" @click="requestMediaPermissions">
                  请求权限
                </button>
              </div>
              <select v-else v-model="editSession.camera_id">
                <option value="">不更改</option>
                <option
                  v-for="camera in mediaStore.cameras"
                  :key="camera.deviceId"
                  :value="camera.deviceId"
                >
                  {{ camera.label }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label>音频设备</label>
              <select v-model="editSession.audio_device_id" :disabled="!mediaStore.isPermissionGranted">
                <option value="">不更改</option>
                <option
                  v-for="mic in mediaStore.microphones"
                  :key="mic.deviceId"
                  :value="mic.deviceId"
                >
                  {{ mic.label }}
                </option>
              </select>
            </div>
            <div class="form-actions">
              <button type="button" class="hud-button" @click="showEditSession = false">
                取消
              </button>
              <button type="submit" class="hud-button hud-button--primary">
                保存修改
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.dashboard {
  padding: var(--hud-spacing-lg);
  min-height: 100vh;
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hud-spacing-xl);
}

.header-content {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-xs);
}

.title {
  font-size: 28px;
  color: var(--hud-border);
  text-shadow: var(--hud-glow);
  margin: 0;
}

.subtitle {
  color: var(--hud-text-secondary);
  font-size: 14px;
  margin: 0;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--hud-spacing-lg);
  margin-bottom: var(--hud-spacing-xl);
}

.stat-card {
  background: var(--hud-bg);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-md);
  padding: var(--hud-spacing-lg);
  text-align: center;
  transition: var(--hud-transition);
}

.stat-card:hover {
  border-color: var(--hud-border);
  box-shadow: var(--hud-glow);
}

.stat-value {
  display: block;
  font-size: 36px;
  color: var(--hud-border);
  margin-bottom: var(--hud-spacing-xs);
}

.stat-label {
  font-size: 12px;
  color: var(--hud-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--hud-spacing-lg);
}

.module-list {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
}

.module-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
}

.module-name {
  font-size: 13px;
  color: var(--hud-text-primary);
}

.module-status {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 2px 8px;
  border-radius: var(--hud-radius-sm);
}

.status--success {
  color: var(--hud-success);
  background: rgba(0, 255, 136, 0.1);
}

.status--danger {
  color: var(--hud-danger);
  background: rgba(255, 68, 68, 0.1);
}

.status--warning {
  color: var(--hud-warning);
  background: rgba(255, 204, 0, 0.1);
}

.actions-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--hud-spacing-md);
}

.action-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--hud-spacing-lg);
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-md);
  text-decoration: none;
  color: var(--hud-text-primary);
  transition: var(--hud-transition);
}

.action-card:hover {
  border-color: var(--hud-border);
  box-shadow: var(--hud-glow);
  transform: translateY(-2px);
}

.action-icon {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: var(--hud-spacing-sm);
}

.action-label {
  font-size: 13px;
}

.view-all {
  font-size: 12px;
  color: var(--hud-border);
  text-decoration: none;
}

.view-all:hover {
  text-decoration: underline;
}

.report-list {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
}

.report-item {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
}

.report-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.report-trainee {
  font-size: 13px;
  color: var(--hud-text-primary);
}

.report-scenario {
  font-size: 11px;
  color: var(--hud-text-muted);
}

.report-score {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-sm);
}

.score-value {
  font-size: 18px;
  color: var(--hud-border);
}

.score-grade {
  font-size: 12px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: var(--hud-radius-sm);
}

.grade--a { color: var(--hud-success); background: rgba(0, 255, 136, 0.1); }
.grade--b { color: var(--hud-info); background: rgba(0, 212, 255, 0.1); }
.grade--c { color: var(--hud-warning); background: rgba(255, 204, 0, 0.1); }
.grade--d { color: var(--hud-danger); background: rgba(255, 68, 68, 0.1); }

.report-date {
  font-size: 11px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.report-empty {
  text-align: center;
  color: var(--hud-text-muted);
  padding: var(--hud-spacing-lg);
}

/* Session List Panel */
.session-count {
  font-size: 12px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
  max-height: 300px;
  overflow-y: auto;
}

.session-item {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
}

.session-item-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.session-trainee {
  font-size: 13px;
  color: var(--hud-text-primary);
}

.session-id {
  font-size: 11px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.session-status {
  font-size: 11px;
  font-family: var(--font-mono);
  padding: 2px 8px;
  border-radius: var(--hud-radius-sm);
  white-space: nowrap;
}

.session-status--running {
  color: var(--hud-success);
  background: rgba(0, 255, 136, 0.1);
}

.session-status--completed {
  color: var(--hud-info);
  background: rgba(0, 212, 255, 0.1);
}

.session-status--cancelled {
  color: var(--hud-danger);
  background: rgba(255, 68, 68, 0.1);
}

.session-status--paused {
  color: var(--hud-warning);
  background: rgba(255, 204, 0, 0.1);
}

.session-status--created {
  color: var(--hud-text-secondary);
  background: rgba(255, 255, 255, 0.05);
}

.session-date {
  font-size: 11px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
  white-space: nowrap;
}

.session-actions-btns {
  display: flex;
  gap: var(--hud-spacing-xs);
}

.edit-btn,
.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  color: var(--hud-text-muted);
  transition: var(--hud-transition);
}

.edit-btn:hover:not(:disabled) {
  border-color: var(--hud-info);
  color: var(--hud-info);
  background: rgba(0, 212, 255, 0.1);
}

.delete-btn:hover:not(:disabled) {
  border-color: var(--hud-danger);
  color: var(--hud-danger);
  background: rgba(255, 68, 68, 0.1);
}

.edit-btn:disabled,
.delete-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.action-icon {
  width: 16px;
  height: 16px;
}

.session-empty {
  text-align: center;
  color: var(--hud-text-muted);
  padding: var(--hud-spacing-lg);
}

.session-info {
  margin-bottom: var(--hud-spacing-md);
}

.session-info p {
  font-size: 13px;
  color: var(--hud-text-secondary);
  margin: var(--hud-spacing-xs) 0;
}

.session-actions {
  margin-top: var(--hud-spacing-md);
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  width: 100%;
  max-width: 400px;
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--hud-text-muted);
  font-size: 18px;
  cursor: pointer;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-md);
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-xs);
}

.form-group label {
  font-size: 12px;
  color: var(--hud-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.form-group input,
.form-group select {
  background: var(--hud-bg-light);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  color: var(--hud-text-primary);
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--hud-border);
  box-shadow: var(--hud-glow);
}

.form-hint {
  font-size: 11px;
  margin-top: var(--hud-spacing-xs);
  display: block;
}

.form-hint--warning {
  color: var(--hud-warning);
}

.form-hint--info {
  color: var(--hud-info);
}

.permission-request {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
  padding: var(--hud-spacing-md);
  background: rgba(0, 212, 255, 0.05);
  border: 1px solid var(--hud-border-dim);
  border-radius: var(--hud-radius-sm);
}

.hud-button--small {
  padding: var(--hud-spacing-xs) var(--hud-spacing-md);
  font-size: 12px;
}

.form-actions {
  display: flex;
  gap: var(--hud-spacing-md);
  justify-content: flex-end;
  margin-top: var(--hud-spacing-md);
}

@media (max-width: 768px) {
  .stats-row {
    grid-template-columns: 1fr;
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .actions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
