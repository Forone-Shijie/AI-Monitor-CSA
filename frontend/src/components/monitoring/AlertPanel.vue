<script setup lang="ts">
import { computed } from 'vue'
import type { Alert } from '@/types/api'

const props = withDefaults(defineProps<{
  alerts: Alert[]
  maxItems?: number
}>(), {
  maxItems: 5
})

const emit = defineEmits<{
  clear: []
}>()

const displayAlerts = computed(() =>
  props.alerts.slice(0, props.maxItems)
)

function formatTime(timestamp: number): string {
  const date = new Date(timestamp * 1000)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

function getLevelClass(level: string): string {
  return `alert--${level}`
}

function getLevelIcon(level: string): string {
  switch (level) {
    case 'error': return '!'
    case 'warning': return '!'
    case 'info': return 'i'
    default: return '?'
  }
}
</script>

<template>
  <div class="alert-panel">
    <div class="alert-header">
      <span class="alert-title">告警信息</span>
      <button
        v-if="alerts.length > 0"
        class="clear-btn"
        @click="emit('clear')"
      >
        清除
      </button>
    </div>

    <div class="alert-list" v-if="displayAlerts.length > 0">
      <TransitionGroup name="alert">
        <div
          v-for="(alert, index) in displayAlerts"
          :key="`${alert.timestamp}-${index}`"
          class="alert-item"
          :class="getLevelClass(alert.level)"
        >
          <span class="alert-icon">{{ getLevelIcon(alert.level) }}</span>
          <span class="alert-message">{{ alert.message }}</span>
          <span class="alert-time hud-number">{{ formatTime(alert.timestamp) }}</span>
        </div>
      </TransitionGroup>
    </div>

    <div v-else class="alert-empty">
      <span class="empty-icon">-</span>
      <span class="empty-text">暂无告警</span>
    </div>

    <div v-if="alerts.length > maxItems" class="alert-more">
      还有 {{ alerts.length - maxItems }} 条告警
    </div>
  </div>
</template>

<style scoped>
.alert-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.alert-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hud-spacing-md);
}

.alert-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--hud-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.clear-btn {
  background: transparent;
  border: 1px solid var(--hud-border-dim);
  color: var(--hud-text-muted);
  padding: 2px 8px;
  font-size: 11px;
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  transition: var(--hud-transition);
}

.clear-btn:hover {
  border-color: var(--hud-border);
  color: var(--hud-border);
}

.alert-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
  overflow-y: auto;
}

.alert-item {
  display: flex;
  align-items: flex-start;
  gap: var(--hud-spacing-sm);
  padding: var(--hud-spacing-sm);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
  border-left: 3px solid;
}

.alert--error {
  border-color: var(--hud-danger);
  background: rgba(255, 68, 68, 0.1);
}

.alert--warning {
  border-color: var(--hud-warning);
  background: rgba(255, 204, 0, 0.1);
}

.alert--info {
  border-color: var(--hud-info);
  background: rgba(0, 212, 255, 0.05);
}

.alert-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: 700;
  border-radius: 50%;
  flex-shrink: 0;
}

.alert--error .alert-icon {
  background: var(--hud-danger);
  color: white;
}

.alert--warning .alert-icon {
  background: var(--hud-warning);
  color: var(--hud-bg-dark);
}

.alert--info .alert-icon {
  background: var(--hud-info);
  color: var(--hud-bg-dark);
}

.alert-message {
  flex: 1;
  font-size: 12px;
  color: var(--hud-text-primary);
  line-height: 1.4;
}

.alert-time {
  font-size: 10px;
  color: var(--hud-text-muted);
  flex-shrink: 0;
}

.alert-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--hud-spacing-sm);
  color: var(--hud-text-muted);
}

.empty-icon {
  font-size: 24px;
  opacity: 0.5;
}

.empty-text {
  font-size: 12px;
}

.alert-more {
  text-align: center;
  font-size: 11px;
  color: var(--hud-text-muted);
  padding-top: var(--hud-spacing-sm);
  border-top: 1px solid var(--hud-border-dim);
  margin-top: var(--hud-spacing-sm);
}

/* Transition animations */
.alert-enter-active,
.alert-leave-active {
  transition: all 0.3s ease;
}

.alert-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}

.alert-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
</style>
