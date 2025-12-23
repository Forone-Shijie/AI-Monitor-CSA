<script setup lang="ts">
import { computed } from 'vue'
import type { RealtimeScores } from '@/types/api'

const props = withDefaults(defineProps<{
  scores: RealtimeScores
  showTotal?: boolean
  compact?: boolean
}>(), {
  showTotal: true,
  compact: false
})

const dimensions = computed(() => [
  { key: 'pose', label: '姿态标准', weight: '30%', color: '#00d4ff' },
  { key: 'action', label: '动作时效', weight: '40%', color: '#00ff88' },
  { key: 'communication', label: '沟通协同', weight: '30%', color: '#ffcc00' }
])

function getScoreColor(score: number): string {
  if (score >= 90) return '#00ff88'
  if (score >= 80) return '#00d4ff'
  if (score >= 70) return '#ffcc00'
  if (score >= 60) return '#ff9944'
  return '#ff4444'
}

function getGrade(score: number): string {
  if (score >= 90) return 'A'
  if (score >= 80) return 'B'
  if (score >= 70) return 'C'
  if (score >= 60) return 'D'
  return 'F'
}
</script>

<template>
  <div class="score-panel" :class="{ 'score-panel--compact': compact }">
    <!-- Total Score -->
    <div v-if="showTotal" class="total-score">
      <div class="score-ring" :style="{ '--score-color': getScoreColor(scores.total) }">
        <svg viewBox="0 0 100 100">
          <circle cx="50" cy="50" r="45" class="ring-bg" />
          <circle
            cx="50"
            cy="50"
            r="45"
            class="ring-progress"
            :style="{
              strokeDashoffset: 283 - (283 * scores.total) / 100,
              stroke: getScoreColor(scores.total)
            }"
          />
        </svg>
        <div class="score-value">
          <span class="score-number hud-number">{{ Math.round(scores.total) }}</span>
          <span class="score-grade">{{ getGrade(scores.total) }}</span>
        </div>
      </div>
      <div class="score-label">综合评分</div>
    </div>

    <!-- Dimension Scores -->
    <div class="dimension-scores">
      <div
        v-for="dim in dimensions"
        :key="dim.key"
        class="dimension-item"
      >
        <div class="dimension-header">
          <span class="dimension-label">{{ dim.label }}</span>
          <span class="dimension-weight">{{ dim.weight }}</span>
        </div>
        <div class="dimension-bar">
          <div
            class="dimension-progress"
            :style="{
              width: `${scores[dim.key as keyof RealtimeScores]}%`,
              backgroundColor: dim.color
            }"
          ></div>
        </div>
        <div class="dimension-value hud-number">
          {{ Math.round(scores[dim.key as keyof RealtimeScores]) }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.score-panel {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-lg);
}

.score-panel--compact {
  flex-direction: row;
  align-items: center;
}

.score-panel--compact .total-score {
  flex-shrink: 0;
}

.score-panel--compact .dimension-scores {
  flex: 1;
}

.total-score {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hud-spacing-sm);
}

.score-ring {
  position: relative;
  width: 120px;
  height: 120px;
}

.score-ring svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}

.ring-bg {
  fill: none;
  stroke: var(--hud-bg-light);
  stroke-width: 8;
}

.ring-progress {
  fill: none;
  stroke-width: 8;
  stroke-linecap: round;
  stroke-dasharray: 283;
  transition: stroke-dashoffset 0.5s ease, stroke 0.3s ease;
  filter: drop-shadow(0 0 6px var(--score-color));
}

.score-value {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}

.score-number {
  display: block;
  font-size: 32px;
  font-weight: 700;
  color: var(--hud-text-primary);
}

.score-grade {
  display: block;
  font-size: 14px;
  color: var(--hud-text-secondary);
  margin-top: -4px;
}

.score-label {
  font-size: 14px;
  color: var(--hud-text-secondary);
}

.dimension-scores {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-md);
}

.dimension-item {
  display: grid;
  grid-template-columns: 1fr auto;
  grid-template-rows: auto auto;
  gap: var(--hud-spacing-xs);
  align-items: center;
}

.dimension-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.dimension-label {
  font-size: 13px;
  color: var(--hud-text-primary);
}

.dimension-weight {
  font-size: 11px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.dimension-bar {
  grid-column: 1;
  height: 6px;
  background: var(--hud-bg-light);
  border-radius: 3px;
  overflow: hidden;
}

.dimension-progress {
  height: 100%;
  border-radius: 3px;
  transition: width 0.3s ease;
  box-shadow: 0 0 8px currentColor;
}

.dimension-value {
  grid-column: 2;
  grid-row: 1 / 3;
  font-size: 20px;
  font-weight: 600;
  color: var(--hud-border);
  min-width: 40px;
  text-align: right;
}

.score-panel--compact .score-ring {
  width: 80px;
  height: 80px;
}

.score-panel--compact .score-number {
  font-size: 24px;
}

.score-panel--compact .dimension-value {
  font-size: 16px;
}
</style>
