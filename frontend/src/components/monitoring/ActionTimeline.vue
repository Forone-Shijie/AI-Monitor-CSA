<script setup lang="ts">
import { computed } from 'vue'
import type { TimelineEvent, ActionData } from '@/types/api'

const props = withDefaults(defineProps<{
  events?: TimelineEvent[]
  actions?: ActionData[]
  duration: number
  currentTime?: number
}>(), {
  events: () => [],
  actions: () => [],
  currentTime: 0
})

const emit = defineEmits<{
  seek: [time: number]
}>()

const timelineItems = computed(() => {
  const items: Array<{
    id: string
    time: number
    label: string
    type: string
    position: number
  }> = []

  // Add action events
  for (const action of props.actions) {
    items.push({
      id: `action-${action.timestamp}`,
      time: action.timestamp,
      label: action.action_name,
      type: 'action',
      position: (action.timestamp / props.duration) * 100
    })
  }

  // Add timeline events
  for (const event of props.events) {
    items.push({
      id: `event-${event.timestamp}-${event.type}`,
      time: event.timestamp,
      label: event.label,
      type: event.type,
      position: (event.timestamp / props.duration) * 100
    })
  }

  return items.sort((a, b) => a.time - b.time)
})

const currentPosition = computed(() =>
  (props.currentTime / props.duration) * 100
)

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function handleClick(event: MouseEvent) {
  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const x = event.clientX - rect.left
  const percentage = x / rect.width
  const time = percentage * props.duration
  emit('seek', time)
}

function getTypeColor(type: string): string {
  switch (type) {
    case 'action': return 'var(--hud-success)'
    case 'alert': return 'var(--hud-danger)'
    case 'asr': return 'var(--hud-info)'
    case 'pose_change': return 'var(--hud-warning)'
    default: return 'var(--hud-border)'
  }
}
</script>

<template>
  <div class="action-timeline">
    <div class="timeline-header">
      <span class="timeline-title">动作时间轴</span>
      <span class="timeline-time hud-number">
        {{ formatTime(currentTime) }} / {{ formatTime(duration) }}
      </span>
    </div>

    <div class="timeline-track" @click="handleClick">
      <!-- Progress bar -->
      <div
        class="timeline-progress"
        :style="{ width: `${currentPosition}%` }"
      ></div>

      <!-- Current position indicator -->
      <div
        class="timeline-cursor"
        :style="{ left: `${currentPosition}%` }"
      ></div>

      <!-- Event markers -->
      <div
        v-for="item in timelineItems"
        :key="item.id"
        class="timeline-marker"
        :style="{
          left: `${item.position}%`,
          backgroundColor: getTypeColor(item.type)
        }"
        :title="`${formatTime(item.time)} - ${item.label}`"
      ></div>
    </div>

    <!-- Event list -->
    <div class="timeline-events" v-if="timelineItems.length > 0">
      <div
        v-for="item in timelineItems.slice(0, 5)"
        :key="item.id"
        class="event-item"
        :class="`event--${item.type}`"
        @click="emit('seek', item.time)"
      >
        <span class="event-time hud-number">{{ formatTime(item.time) }}</span>
        <span class="event-label">{{ item.label }}</span>
      </div>
    </div>

    <div v-else class="timeline-empty">
      暂无动作记录
    </div>
  </div>
</template>

<style scoped>
.action-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-md);
}

.timeline-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.timeline-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--hud-text-secondary);
  text-transform: uppercase;
  letter-spacing: 1px;
}

.timeline-time {
  font-size: 14px;
  color: var(--hud-border);
}

.timeline-track {
  position: relative;
  height: 24px;
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  overflow: hidden;
}

.timeline-track:hover {
  background: rgba(0, 212, 255, 0.1);
}

.timeline-progress {
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  background: linear-gradient(
    90deg,
    rgba(0, 212, 255, 0.3) 0%,
    rgba(0, 212, 255, 0.1) 100%
  );
  pointer-events: none;
}

.timeline-cursor {
  position: absolute;
  top: 0;
  width: 2px;
  height: 100%;
  background: var(--hud-border);
  box-shadow: 0 0 8px var(--hud-border);
  pointer-events: none;
  transform: translateX(-50%);
}

.timeline-marker {
  position: absolute;
  top: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transform: translate(-50%, -50%);
  cursor: pointer;
  transition: transform 0.2s ease;
}

.timeline-marker:hover {
  transform: translate(-50%, -50%) scale(1.5);
}

.timeline-events {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-xs);
  max-height: 150px;
  overflow-y: auto;
}

.event-item {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-sm);
  padding: var(--hud-spacing-sm);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  transition: var(--hud-transition);
  border-left: 3px solid transparent;
}

.event-item:hover {
  background: rgba(0, 212, 255, 0.1);
}

.event--action {
  border-color: var(--hud-success);
}

.event--alert {
  border-color: var(--hud-danger);
}

.event--asr {
  border-color: var(--hud-info);
}

.event--pose_change {
  border-color: var(--hud-warning);
}

.event-time {
  font-size: 11px;
  color: var(--hud-text-muted);
  min-width: 45px;
}

.event-label {
  font-size: 12px;
  color: var(--hud-text-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.timeline-empty {
  text-align: center;
  font-size: 12px;
  color: var(--hud-text-muted);
  padding: var(--hud-spacing-md);
}
</style>
