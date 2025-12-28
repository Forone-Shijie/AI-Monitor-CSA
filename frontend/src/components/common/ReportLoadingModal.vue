<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'complete'): void
}>()

const loadingMessages = [
  '正在停止监测...',
  '正在分析姿态数据...',
  '正在评估动作序列...',
  '正在处理语音数据...',
  'AI 正在生成改进建议...',
  '正在生成评估报告...',
  '即将跳转至报告页面...'
]

const currentMessageIndex = ref(0)
const progress = ref(0)
let interval: number | null = null

function startAnimation() {
  currentMessageIndex.value = 0
  progress.value = 0

  interval = window.setInterval(() => {
    if (currentMessageIndex.value < loadingMessages.length - 1) {
      currentMessageIndex.value++
      progress.value = ((currentMessageIndex.value + 1) / loadingMessages.length) * 100
    }
  }, 600)
}

function stopAnimation() {
  if (interval) {
    clearInterval(interval)
    interval = null
  }
}

watch(() => props.visible, (visible) => {
  if (visible) {
    startAnimation()
  } else {
    stopAnimation()
  }
})

onUnmounted(() => {
  stopAnimation()
})

function complete() {
  currentMessageIndex.value = loadingMessages.length - 1
  progress.value = 100
  stopAnimation()
  setTimeout(() => {
    emit('complete')
  }, 400)
}

defineExpose({ complete })
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="loading-overlay">
        <div class="loading-modal">
          <div class="loading-icon">
            <div class="spinner"></div>
            <div class="pulse-ring"></div>
          </div>
          <h2 class="loading-title">AI 报告生成中</h2>
          <p class="loading-message">{{ loadingMessages[currentMessageIndex] }}</p>
          <div class="progress-bar">
            <div class="progress-fill" :style="{ width: `${progress}%` }"></div>
          </div>
          <p class="loading-hint">请稍候，AI正在分析您的训练数据...</p>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(10, 22, 40, 0.95);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.loading-modal {
  text-align: center;
  max-width: 400px;
  padding: 48px;
}

.loading-icon {
  position: relative;
  width: 80px;
  height: 80px;
  margin: 0 auto 32px;
}

.spinner {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 64px;
  height: 64px;
  border: 3px solid rgba(0, 212, 255, 0.2);
  border-top-color: var(--hud-border, #00d4ff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.pulse-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 80px;
  height: 80px;
  border: 2px solid var(--hud-border, #00d4ff);
  border-radius: 50%;
  animation: pulse 2s ease-out infinite;
  opacity: 0;
}

@keyframes spin {
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

@keyframes pulse {
  0% {
    transform: translate(-50%, -50%) scale(0.8);
    opacity: 0.8;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.4);
    opacity: 0;
  }
}

.loading-title {
  color: var(--hud-border, #00d4ff);
  font-size: 24px;
  margin-bottom: 16px;
  font-weight: 500;
}

.loading-message {
  color: var(--hud-text-primary, #e0e0e0);
  font-size: 16px;
  margin-bottom: 24px;
  min-height: 24px;
  transition: opacity 0.3s;
}

.progress-bar {
  width: 100%;
  height: 4px;
  background: rgba(0, 212, 255, 0.2);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 16px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--hud-border, #00d4ff), #00ff88);
  transition: width 0.5s ease-out;
  box-shadow: 0 0 10px var(--hud-border, #00d4ff);
}

.loading-hint {
  color: var(--hud-text-muted, #888);
  font-size: 12px;
}

/* Transition */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
