<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useReportStore } from '@/stores/report'
import RadarChart from '@/components/charts/RadarChart.vue'
import ScorePanel from '@/components/monitoring/ScorePanel.vue'
import type { ReportData, Suggestion } from '@/types/api'

const reportStore = useReportStore()

const selectedReportId = ref<string | null>(null)
const isLoading = ref(false)

const reports = computed(() => reportStore.reports)
const currentReport = computed<ReportData | null>(() => reportStore.currentReport)

const currentScores = computed(() => {
  if (!currentReport.value?.evaluation?.scores) {
    return { pose: 0, action: 0, communication: 0, total: 0 }
  }
  const scores = currentReport.value.evaluation.scores
  return {
    pose: scores.pose.score,
    action: scores.action.score,
    communication: scores.communication.score,
    total: scores.total
  }
})

const suggestions = computed<Suggestion[]>(() =>
  currentReport.value?.suggestions || []
)

const highPrioritySuggestions = computed(() =>
  suggestions.value.filter(s => s.priority === 'high')
)

const otherSuggestions = computed(() =>
  suggestions.value.filter(s => s.priority !== 'high')
)

async function loadReports() {
  isLoading.value = true
  try {
    await reportStore.fetchReports()
  } catch (error) {
    console.error('Failed to load reports:', error)
  } finally {
    isLoading.value = false
  }
}

async function selectReport(reportId: string) {
  selectedReportId.value = reportId
  isLoading.value = true
  try {
    await reportStore.fetchReport(reportId)
  } catch (error) {
    console.error('Failed to load report:', error)
  } finally {
    isLoading.value = false
  }
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

function getGradeClass(grade: string): string {
  return `grade--${grade.toLowerCase()}`
}

function getPriorityClass(priority: string): string {
  return `priority--${priority}`
}

function getPriorityLabel(priority: string): string {
  switch (priority) {
    case 'high': return '重要'
    case 'medium': return '建议'
    case 'low': return '参考'
    default: return priority
  }
}

function getDimensionLabel(dimension: string): string {
  switch (dimension) {
    case 'pose': return '姿态'
    case 'action': return '动作'
    case 'communication': return '沟通'
    default: return dimension
  }
}

onMounted(loadReports)
</script>

<template>
  <div class="reports-page">
    <!-- Header -->
    <header class="page-header">
      <h1>评估报告</h1>
      <div class="header-stats" v-if="reports.length > 0">
        <span class="stat">共 <span class="hud-number">{{ reports.length }}</span> 份报告</span>
        <span class="stat">平均分 <span class="hud-number">{{ reportStore.averageScore }}</span></span>
      </div>
    </header>

    <div class="reports-content">
      <!-- Left: Report List -->
      <div class="report-list-section">
        <div class="hud-panel list-panel">
          <div class="hud-panel-header">
            <span class="hud-panel-title">报告列表</span>
          </div>

          <div v-if="isLoading && reports.length === 0" class="loading">
            加载中...
          </div>

          <div v-else-if="reports.length === 0" class="empty-list">
            暂无评估报告
          </div>

          <div v-else class="report-list">
            <div
              v-for="report in reports"
              :key="report.report_id"
              class="report-item"
              :class="{ 'report-item--active': selectedReportId === report.report_id }"
              @click="selectReport(report.session_id)"
            >
              <div class="report-main">
                <span class="report-trainee">{{ report.trainee_name }}</span>
                <span class="report-scenario">{{ report.scenario_name }}</span>
              </div>
              <div class="report-meta">
                <div class="report-score">
                  <span class="score-value hud-number">{{ report.total_score }}</span>
                  <span class="score-grade" :class="getGradeClass(report.grade)">
                    {{ report.grade }}
                  </span>
                </div>
                <span class="report-date">{{ formatDate(report.generated_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Right: Report Detail -->
      <div class="report-detail-section">
        <!-- No Selection -->
        <div v-if="!currentReport" class="no-selection">
          <div class="hud-panel">
            <div class="no-selection-icon">A</div>
            <h2>请选择报告</h2>
            <p>从左侧列表选择一份报告查看详情</p>
          </div>
        </div>

        <!-- Report Detail -->
        <template v-else>
          <!-- Header Info -->
          <div class="hud-panel header-panel">
            <div class="detail-header">
              <div class="trainee-info">
                <h2>{{ currentReport.trainee_name }}</h2>
                <span class="trainee-id">{{ currentReport.trainee_id }}</span>
              </div>
              <div class="score-display">
                <span class="total-score hud-number">{{ currentScores.total }}</span>
                <span class="grade-badge" :class="getGradeClass(currentReport.evaluation.grade)">
                  {{ currentReport.evaluation.grade }}
                </span>
              </div>
            </div>
            <div class="detail-meta">
              <span>场景: {{ currentReport.scenario_name }}</span>
              <span>生成时间: {{ formatDate(currentReport.generated_at) }}</span>
            </div>
          </div>

          <!-- Scores & Chart -->
          <div class="scores-section">
            <div class="hud-panel chart-panel">
              <div class="hud-panel-header">
                <span class="hud-panel-title">能力雷达图</span>
              </div>
              <RadarChart :scores="currentReport.evaluation.scores" height="280px" />
            </div>

            <div class="hud-panel scores-panel">
              <div class="hud-panel-header">
                <span class="hud-panel-title">分数明细</span>
              </div>
              <ScorePanel :scores="currentScores" />
            </div>
          </div>

          <!-- Suggestions -->
          <div class="hud-panel suggestions-panel">
            <div class="hud-panel-header">
              <span class="hud-panel-title">AI改进建议</span>
              <span class="suggestion-count">{{ suggestions.length }} 条建议</span>
            </div>

            <!-- High Priority -->
            <div v-if="highPrioritySuggestions.length > 0" class="suggestion-group">
              <h4 class="group-title">重点改进</h4>
              <div
                v-for="(suggestion, index) in highPrioritySuggestions"
                :key="`high-${index}`"
                class="suggestion-item"
                :class="getPriorityClass(suggestion.priority)"
              >
                <div class="suggestion-header">
                  <span class="suggestion-dimension">{{ getDimensionLabel(suggestion.dimension) }}</span>
                  <span class="suggestion-priority">{{ getPriorityLabel(suggestion.priority) }}</span>
                </div>
                <div class="suggestion-issue">{{ suggestion.issue }}</div>
                <div class="suggestion-recommendation">{{ suggestion.recommendation }}</div>
                <div v-if="suggestion.reference" class="suggestion-reference">
                  参考: {{ suggestion.reference }}
                </div>
              </div>
            </div>

            <!-- Other Suggestions -->
            <div v-if="otherSuggestions.length > 0" class="suggestion-group">
              <h4 class="group-title">其他建议</h4>
              <div
                v-for="(suggestion, index) in otherSuggestions"
                :key="`other-${index}`"
                class="suggestion-item"
                :class="getPriorityClass(suggestion.priority)"
              >
                <div class="suggestion-header">
                  <span class="suggestion-dimension">{{ getDimensionLabel(suggestion.dimension) }}</span>
                  <span class="suggestion-priority">{{ getPriorityLabel(suggestion.priority) }}</span>
                </div>
                <div class="suggestion-issue">{{ suggestion.issue }}</div>
                <div class="suggestion-recommendation">{{ suggestion.recommendation }}</div>
              </div>
            </div>

            <div v-if="suggestions.length === 0" class="no-suggestions">
              暂无改进建议
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.reports-page {
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

.header-stats {
  display: flex;
  gap: var(--hud-spacing-lg);
}

.stat {
  font-size: 13px;
  color: var(--hud-text-secondary);
}

.stat .hud-number {
  color: var(--hud-border);
  font-size: 16px;
}

.reports-content {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: var(--hud-spacing-lg);
}

.list-panel {
  max-height: calc(100vh - 150px);
  display: flex;
  flex-direction: column;
}

.report-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
}

.report-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border: 1px solid transparent;
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  transition: var(--hud-transition);
}

.report-item:hover {
  border-color: var(--hud-border-dim);
}

.report-item--active {
  border-color: var(--hud-border);
  box-shadow: var(--hud-glow);
}

.report-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.report-trainee {
  font-size: 14px;
  color: var(--hud-text-primary);
  font-weight: 500;
}

.report-scenario {
  font-size: 12px;
  color: var(--hud-text-muted);
}

.report-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--hud-spacing-xs);
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
.grade--d, .grade--f { color: var(--hud-danger); background: rgba(255, 68, 68, 0.1); }

.report-date {
  font-size: 10px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.loading,
.empty-list {
  text-align: center;
  color: var(--hud-text-muted);
  padding: var(--hud-spacing-xl);
}

.report-detail-section {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-lg);
}

.no-selection {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.no-selection .hud-panel {
  text-align: center;
  max-width: 300px;
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

.header-panel {
  padding: var(--hud-spacing-lg);
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--hud-spacing-md);
}

.trainee-info h2 {
  font-size: 24px;
  color: var(--hud-text-primary);
  margin: 0 0 var(--hud-spacing-xs) 0;
}

.trainee-id {
  font-size: 12px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.score-display {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
}

.total-score {
  font-size: 48px;
  color: var(--hud-border);
  text-shadow: var(--hud-glow);
}

.grade-badge {
  font-size: 24px;
  font-weight: 700;
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  border-radius: var(--hud-radius-md);
}

.detail-meta {
  display: flex;
  gap: var(--hud-spacing-lg);
  font-size: 13px;
  color: var(--hud-text-secondary);
}

.scores-section {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--hud-spacing-lg);
}

.suggestion-count {
  font-size: 12px;
  color: var(--hud-text-muted);
}

.suggestion-group {
  margin-bottom: var(--hud-spacing-lg);
}

.group-title {
  font-size: 13px;
  color: var(--hud-text-secondary);
  margin: 0 0 var(--hud-spacing-md) 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.suggestion-item {
  padding: var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border-radius: var(--hud-radius-sm);
  margin-bottom: var(--hud-spacing-sm);
  border-left: 3px solid;
}

.priority--high {
  border-color: var(--hud-danger);
}

.priority--medium {
  border-color: var(--hud-warning);
}

.priority--low {
  border-color: var(--hud-info);
}

.suggestion-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--hud-spacing-sm);
}

.suggestion-dimension {
  font-size: 12px;
  color: var(--hud-border);
  font-weight: 500;
}

.suggestion-priority {
  font-size: 10px;
  padding: 2px 6px;
  border-radius: var(--hud-radius-sm);
}

.priority--high .suggestion-priority {
  background: rgba(255, 68, 68, 0.1);
  color: var(--hud-danger);
}

.priority--medium .suggestion-priority {
  background: rgba(255, 204, 0, 0.1);
  color: var(--hud-warning);
}

.priority--low .suggestion-priority {
  background: rgba(0, 212, 255, 0.1);
  color: var(--hud-info);
}

.suggestion-issue {
  font-size: 14px;
  color: var(--hud-text-primary);
  margin-bottom: var(--hud-spacing-sm);
}

.suggestion-recommendation {
  font-size: 13px;
  color: var(--hud-text-secondary);
  line-height: 1.5;
}

.suggestion-reference {
  font-size: 11px;
  color: var(--hud-text-muted);
  margin-top: var(--hud-spacing-sm);
  font-style: italic;
}

.no-suggestions {
  text-align: center;
  color: var(--hud-text-muted);
  padding: var(--hud-spacing-lg);
}

@media (max-width: 1024px) {
  .reports-content {
    grid-template-columns: 1fr;
  }

  .scores-section {
    grid-template-columns: 1fr;
  }
}
</style>
