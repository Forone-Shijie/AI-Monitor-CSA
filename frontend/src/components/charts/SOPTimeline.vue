<script setup lang="ts">
import { computed } from 'vue'
import type { BracePositionTimeline, BraceStepStatus } from '@/types/api'

const props = defineProps<{
  timeline: BracePositionTimeline
}>()

// Calculate the total timeline duration for scaling
const totalDuration = computed(() => {
  // Use the larger of: standard completion time + hold, or actual total time
  const standardTotal = 5 + props.timeline.hold_duration.required // 5s completion + 30s hold
  const actualTotal = props.timeline.total_time
  return Math.max(standardTotal, actualTotal, 40) // At least 40 seconds for display
})

// Get width percentage for a time value
function getWidthPercent(time: number): number {
  return (time / totalDuration.value) * 100
}

// Get position percentage for a time value
function getPositionPercent(time: number): number {
  return (time / totalDuration.value) * 100
}

// Standard step widths (cumulative to individual)
const standardStepWidths = computed(() => {
  const steps = props.timeline.steps
  return steps.map((step, idx) => {
    const prevStep = steps[idx - 1]
    const prevTime = idx === 0 || !prevStep ? 0 : prevStep.standard_time
    return step.standard_time - prevTime
  })
})

// Actual step widths
const actualStepWidths = computed(() => {
  const steps = props.timeline.steps
  return steps.map((step, idx) => {
    if (step.actual_time === null) return 0
    const prevStep = steps[idx - 1]
    const prevTime = idx === 0 || !prevStep ? 0 : (prevStep.actual_time ?? 0)
    return step.actual_time - prevTime
  })
})

// Standard hold bar width (30 seconds)
const standardHoldWidth = computed(() => {
  return getWidthPercent(props.timeline.hold_duration.required)
})

// Actual hold bar width
const actualHoldWidth = computed(() => {
  return getWidthPercent(props.timeline.hold_duration.actual)
})

// Standard hold position (after all steps)
const standardHoldPosition = computed(() => {
  const lastStep = props.timeline.steps[props.timeline.steps.length - 1]
  return lastStep ? getPositionPercent(lastStep.standard_time) : 0
})

// Actual hold position
const actualHoldPosition = computed(() => {
  const lastStep = props.timeline.steps[props.timeline.steps.length - 1]
  return lastStep ? getPositionPercent(lastStep.actual_time ?? 0) : 0
})

// Check if hold duration is compliant
const isHoldCompliant = computed(() => {
  return props.timeline.hold_duration.actual >= props.timeline.hold_duration.required
})

// Format time display
function formatTime(seconds: number): string {
  return `${seconds.toFixed(1)}s`
}

// Get step color based on compliance
function getStepClass(step: BraceStepStatus): string {
  if (step.actual_time === null) return 'step--missed'
  if (!step.is_compliant) return 'step--deviation'
  return 'step--compliant'
}

// Time markers for the timeline
const timeMarkers = computed(() => {
  const total = totalDuration.value
  const markers: number[] = []
  for (let t = 0; t <= total; t += 5) {
    markers.push(t)
  }
  return markers
})

// Get standard step left position
function getStandardStepLeft(idx: number): number {
  if (idx === 0) return 0
  const prevStep = props.timeline.steps[idx - 1]
  return prevStep ? getPositionPercent(prevStep.standard_time) : 0
}

// Get actual step left position
function getActualStepLeft(idx: number): number {
  if (idx === 0) return 0
  const prevStep = props.timeline.steps[idx - 1]
  return prevStep ? getPositionPercent(prevStep.actual_time ?? 0) : 0
}

// Get step width safely
function getStepWidth(widths: number[], idx: number): number {
  return widths[idx] ?? 0
}
</script>

<template>
  <div class="sop-timeline">
    <div class="timeline-header">
      <h3 class="timeline-title">{{ timeline.direction_name }}</h3>
      <div class="timeline-status" :class="timeline.overall_compliant ? 'status--pass' : 'status--fail'">
        {{ timeline.overall_compliant ? '合规' : '需改进' }}
      </div>
    </div>

    <!-- Standard Timeline -->
    <div class="timeline-section">
      <div class="section-label">标准流程</div>
      <div class="timeline-track">
        <!-- Step blocks -->
        <div
          v-for="(step, idx) in timeline.steps"
          :key="`std-${step.step_id}`"
          class="step-block step--standard"
          :style="{
            left: `${getStandardStepLeft(idx)}%`,
            width: `${getStepWidth(standardStepWidths, idx)}%`
          }"
          :title="`${step.step_name}: ${formatTime(step.standard_time)}`"
        >
          <span class="step-label">{{ step.step_id }}</span>
        </div>

        <!-- Hold duration bar -->
        <div
          class="hold-bar hold--standard"
          :style="{
            left: `${standardHoldPosition}%`,
            width: `${standardHoldWidth}%`
          }"
          :title="`保持姿势: ${timeline.hold_duration.required}s`"
        >
          <span class="hold-label">保持 {{ timeline.hold_duration.required }}s</span>
        </div>

        <!-- Time markers -->
        <div class="time-axis">
          <div
            v-for="t in timeMarkers"
            :key="`marker-${t}`"
            class="time-marker"
            :style="{ left: `${getPositionPercent(t)}%` }"
          >
            <span class="marker-line"></span>
            <span class="marker-label">{{ t }}s</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Actual Timeline -->
    <div class="timeline-section">
      <div class="section-label">实际执行</div>
      <div class="timeline-track">
        <!-- Step blocks -->
        <div
          v-for="(step, idx) in timeline.steps"
          :key="`act-${step.step_id}`"
          class="step-block"
          :class="getStepClass(step)"
          :style="{
            left: `${getActualStepLeft(idx)}%`,
            width: `${getStepWidth(actualStepWidths, idx)}%`
          }"
          :title="`${step.step_name}: ${step.actual_time !== null ? formatTime(step.actual_time) : '未完成'}${step.deviation ? ' - ' + step.deviation : ''}`"
        >
          <span class="step-icon">{{ step.is_compliant ? '✓' : '✗' }}</span>
          <span class="step-label">{{ step.step_id }}</span>
        </div>

        <!-- Hold duration bar -->
        <div
          class="hold-bar"
          :class="isHoldCompliant ? 'hold--compliant' : 'hold--deviation'"
          :style="{
            left: `${actualHoldPosition}%`,
            width: `${actualHoldWidth}%`
          }"
          :title="`保持姿势: ${timeline.hold_duration.actual}s`"
        >
          <span class="hold-label">{{ timeline.hold_duration.actual }}s</span>
          <span v-if="!isHoldCompliant" class="hold-warning">不足</span>
        </div>
      </div>
    </div>

    <!-- Step Details -->
    <div class="step-details">
      <div class="details-header">动作步骤详情</div>
      <div class="details-grid">
        <div
          v-for="step in timeline.steps"
          :key="`detail-${step.step_id}`"
          class="detail-item"
          :class="{ 'detail--issue': !step.is_compliant }"
        >
          <div class="detail-step">{{ step.step_id }}. {{ step.step_name }}</div>
          <div class="detail-time">
            <span class="time-label">标准:</span>
            <span class="time-value">{{ formatTime(step.standard_time) }}</span>
            <span class="time-sep">|</span>
            <span class="time-label">实际:</span>
            <span class="time-value" :class="{ 'time--late': step.actual_time && step.actual_time > step.standard_time + 1 }">
              {{ step.actual_time !== null ? formatTime(step.actual_time) : '未完成' }}
            </span>
          </div>
          <div v-if="step.deviation" class="detail-deviation">
            {{ step.deviation }}
          </div>
        </div>
      </div>
    </div>

    <!-- Issues Summary -->
    <div v-if="timeline.issues_summary && timeline.issues_summary.length > 0" class="issues-summary">
      <div class="issues-header">问题汇总</div>
      <ul class="issues-list">
        <li v-for="(issue, idx) in timeline.issues_summary" :key="idx" class="issue-item">
          {{ issue }}
        </li>
      </ul>
    </div>

    <!-- Legend -->
    <div class="timeline-legend">
      <div class="legend-item">
        <span class="legend-color legend--compliant"></span>
        <span class="legend-label">合规</span>
      </div>
      <div class="legend-item">
        <span class="legend-color legend--deviation"></span>
        <span class="legend-label">偏差</span>
      </div>
      <div class="legend-item">
        <span class="legend-color legend--standard"></span>
        <span class="legend-label">标准</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sop-timeline {
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
  font-size: 16px;
  font-weight: 600;
  color: var(--hud-text-primary);
  margin: 0;
}

.timeline-status {
  font-size: 12px;
  font-weight: 600;
  padding: var(--hud-spacing-xs) var(--hud-spacing-sm);
  border-radius: var(--hud-radius-sm);
}

.status--pass {
  background: rgba(0, 255, 136, 0.15);
  color: var(--hud-success);
}

.status--fail {
  background: rgba(255, 68, 68, 0.15);
  color: var(--hud-danger);
}

.timeline-section {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-xs);
}

.section-label {
  font-size: 11px;
  color: var(--hud-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.timeline-track {
  position: relative;
  height: 36px;
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
  overflow: visible;
}

.step-block {
  position: absolute;
  top: 4px;
  height: 20px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 2px;
  font-size: 10px;
  font-weight: 600;
  min-width: 20px;
  transition: all 0.2s;
  cursor: pointer;
}

.step-block:hover {
  transform: scaleY(1.2);
  z-index: 10;
}

.step--standard {
  background: rgba(0, 212, 255, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.5);
  color: var(--hud-border);
}

.step--compliant {
  background: rgba(0, 255, 136, 0.3);
  border: 1px solid rgba(0, 255, 136, 0.5);
  color: var(--hud-success);
}

.step--deviation {
  background: rgba(255, 68, 68, 0.3);
  border: 1px solid rgba(255, 68, 68, 0.5);
  color: var(--hud-danger);
}

.step--missed {
  background: rgba(128, 128, 128, 0.3);
  border: 1px dashed rgba(128, 128, 128, 0.5);
  color: var(--hud-text-muted);
}

.step-icon {
  font-size: 9px;
}

.step-label {
  font-size: 9px;
}

.hold-bar {
  position: absolute;
  top: 4px;
  height: 20px;
  border-radius: 2px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 10px;
  cursor: pointer;
}

.hold--standard {
  background: linear-gradient(90deg, rgba(0, 212, 255, 0.2), rgba(0, 212, 255, 0.1));
  border: 1px dashed rgba(0, 212, 255, 0.4);
  color: var(--hud-border);
}

.hold--compliant {
  background: linear-gradient(90deg, rgba(0, 255, 136, 0.2), rgba(0, 255, 136, 0.1));
  border: 1px solid rgba(0, 255, 136, 0.4);
  color: var(--hud-success);
}

.hold--deviation {
  background: linear-gradient(90deg, rgba(255, 204, 0, 0.2), rgba(255, 204, 0, 0.1));
  border: 1px solid rgba(255, 204, 0, 0.4);
  color: var(--hud-warning);
}

.hold-label {
  font-weight: 500;
}

.hold-warning {
  font-size: 9px;
  padding: 1px 4px;
  background: rgba(255, 204, 0, 0.3);
  border-radius: 2px;
}

.time-axis {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 12px;
}

.time-marker {
  position: absolute;
  transform: translateX(-50%);
}

.marker-line {
  display: block;
  width: 1px;
  height: 4px;
  background: rgba(0, 212, 255, 0.3);
}

.marker-label {
  display: block;
  font-size: 8px;
  color: var(--hud-text-muted);
  text-align: center;
}

.step-details {
  margin-top: var(--hud-spacing-sm);
}

.details-header {
  font-size: 12px;
  color: var(--hud-text-secondary);
  margin-bottom: var(--hud-spacing-sm);
  font-weight: 500;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: var(--hud-spacing-sm);
}

.detail-item {
  padding: var(--hud-spacing-sm);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
  border-left: 3px solid var(--hud-success);
}

.detail--issue {
  border-left-color: var(--hud-danger);
}

.detail-step {
  font-size: 12px;
  color: var(--hud-text-primary);
  margin-bottom: 4px;
}

.detail-time {
  font-size: 11px;
  color: var(--hud-text-muted);
  display: flex;
  gap: 4px;
  align-items: center;
}

.time-label {
  color: var(--hud-text-muted);
}

.time-value {
  color: var(--hud-text-secondary);
  font-family: var(--font-mono);
}

.time--late {
  color: var(--hud-danger);
}

.time-sep {
  color: var(--hud-border-dim);
}

.detail-deviation {
  font-size: 10px;
  color: var(--hud-danger);
  margin-top: 4px;
  font-style: italic;
}

.issues-summary {
  padding: var(--hud-spacing-md);
  background: rgba(255, 68, 68, 0.05);
  border: 1px solid rgba(255, 68, 68, 0.2);
  border-radius: var(--hud-radius-sm);
}

.issues-header {
  font-size: 12px;
  font-weight: 600;
  color: var(--hud-danger);
  margin-bottom: var(--hud-spacing-sm);
}

.issues-list {
  margin: 0;
  padding-left: var(--hud-spacing-md);
}

.issue-item {
  font-size: 12px;
  color: var(--hud-text-secondary);
  margin-bottom: 4px;
}

.issue-item:last-child {
  margin-bottom: 0;
}

.timeline-legend {
  display: flex;
  gap: var(--hud-spacing-lg);
  justify-content: center;
  padding-top: var(--hud-spacing-sm);
  border-top: 1px solid var(--hud-border-dim);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-xs);
}

.legend-color {
  width: 16px;
  height: 10px;
  border-radius: 2px;
}

.legend--compliant {
  background: rgba(0, 255, 136, 0.3);
  border: 1px solid rgba(0, 255, 136, 0.5);
}

.legend--deviation {
  background: rgba(255, 68, 68, 0.3);
  border: 1px solid rgba(255, 68, 68, 0.5);
}

.legend--standard {
  background: rgba(0, 212, 255, 0.3);
  border: 1px solid rgba(0, 212, 255, 0.5);
}

.legend-label {
  font-size: 11px;
  color: var(--hud-text-muted);
}
</style>
