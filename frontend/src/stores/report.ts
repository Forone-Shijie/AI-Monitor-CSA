/**
 * Report Store - Pinia store for evaluation and reports
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  EvaluationData,
  ReportData,
  ReportSummary,
  PlaybackData,
  PlaybackSummary,
  TimelineEvent
} from '@/types/api'
import * as api from '@/services/api'

export const useReportStore = defineStore('report', () => {
  // State
  const reports = ref<ReportSummary[]>([])
  const currentReport = ref<ReportData | null>(null)
  const currentEvaluation = ref<EvaluationData | null>(null)
  const playbackData = ref<PlaybackData | null>(null)
  const playbackSummary = ref<PlaybackSummary | null>(null)
  const timeline = ref<TimelineEvent[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const hasCurrentReport = computed(() => currentReport.value !== null)

  const totalReports = computed(() => reports.value.length)

  const averageScore = computed(() => {
    if (reports.value.length === 0) return 0
    const sum = reports.value.reduce((acc, r) => acc + r.total_score, 0)
    return Math.round(sum / reports.value.length)
  })

  const gradeDistribution = computed(() => {
    const dist: Record<string, number> = { A: 0, B: 0, C: 0, D: 0, F: 0 }
    reports.value.forEach(r => {
      const grade = r.grade
      if (grade in dist) {
        dist[grade] = (dist[grade] ?? 0) + 1
      }
    })
    return dist
  })

  // Actions
  async function fetchReports(traineeId?: string, limit: number = 20) {
    isLoading.value = true
    error.value = null
    try {
      const response = await api.listReports(traineeId, limit)
      reports.value = response.data ?? []
      return response.data ?? []
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch reports'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchReport(reportId: string) {
    isLoading.value = true
    error.value = null
    try {
      currentReport.value = await api.getReport(reportId)
      return currentReport.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch report'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchEvaluation(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      currentEvaluation.value = await api.getEvaluation(sessionId)
      return currentEvaluation.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch evaluation'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function runEvaluation(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      currentEvaluation.value = await api.runEvaluation(sessionId)
      return currentEvaluation.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to run evaluation'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPlaybackData(
    sessionId: string,
    startFrame: number = 0,
    endFrame?: number
  ) {
    isLoading.value = true
    error.value = null
    try {
      playbackData.value = await api.getPlaybackData(sessionId, startFrame, endFrame)
      return playbackData.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch playback data'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchPlaybackSummary(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      playbackSummary.value = await api.getPlaybackSummary(sessionId)
      return playbackSummary.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch playback summary'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchTimeline(sessionId: string) {
    isLoading.value = true
    error.value = null
    try {
      timeline.value = await api.getPlaybackTimeline(sessionId)
      return timeline.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch timeline'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  function reset() {
    currentReport.value = null
    currentEvaluation.value = null
    playbackData.value = null
    playbackSummary.value = null
    timeline.value = []
    error.value = null
  }

  return {
    // State
    reports,
    currentReport,
    currentEvaluation,
    playbackData,
    playbackSummary,
    timeline,
    isLoading,
    error,
    // Computed
    hasCurrentReport,
    totalReports,
    averageScore,
    gradeDistribution,
    // Actions
    fetchReports,
    fetchReport,
    fetchEvaluation,
    runEvaluation,
    fetchPlaybackData,
    fetchPlaybackSummary,
    fetchTimeline,
    reset
  }
})
