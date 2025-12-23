/**
 * Config Store - Pinia store for system configuration
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type {
  SystemConfig,
  ScenarioConfig,
  EvaluationWeights,
  HealthCheck
} from '@/types/api'
import { ASRMode, VideoSourceType } from '@/types/api'
import * as api from '@/services/api'

export const useConfigStore = defineStore('config', () => {
  // State
  const config = ref<SystemConfig | null>(null)
  const scenarios = ref<ScenarioConfig[]>([])
  const weights = ref<EvaluationWeights>({
    pose: 0.3,
    action: 0.4,
    communication: 0.3
  })
  const asrModes = ref<{ current: string; available: { id: string; name: string }[] } | null>(null)
  const healthStatus = ref<HealthCheck | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const isBackendOnline = computed(() =>
    healthStatus.value?.status === 'healthy'
  )

  const currentASRMode = computed(() =>
    config.value?.asr_mode ?? ASRMode.HYBRID
  )

  const currentVideoSource = computed(() =>
    config.value?.video_source ?? VideoSourceType.CAMERA
  )

  const scenarioOptions = computed(() =>
    scenarios.value.map(s => ({
      value: s.id,
      label: s.name,
      description: s.description
    }))
  )

  // Actions
  async function checkHealth() {
    try {
      healthStatus.value = await api.checkHealth()
      return healthStatus.value
    } catch (e) {
      healthStatus.value = {
        status: 'offline',
        sessions: 0
      }
      return null
    }
  }

  async function fetchConfig() {
    isLoading.value = true
    error.value = null
    try {
      config.value = await api.getConfig()
      return config.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch config'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateConfig(updates: Partial<SystemConfig>) {
    isLoading.value = true
    error.value = null
    try {
      config.value = await api.updateConfig(updates)
      return config.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update config'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchScenarios() {
    isLoading.value = true
    error.value = null
    try {
      scenarios.value = await api.getScenarios()
      return scenarios.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch scenarios'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function getScenario(scenarioId: string) {
    try {
      return await api.getScenario(scenarioId)
    } catch (e) {
      console.error('Failed to get scenario:', e)
      return null
    }
  }

  async function fetchWeights() {
    isLoading.value = true
    error.value = null
    try {
      weights.value = await api.getWeights()
      return weights.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch weights'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function updateWeights(newWeights: EvaluationWeights) {
    isLoading.value = true
    error.value = null
    try {
      weights.value = await api.updateWeights(newWeights)
      return weights.value
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update weights'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  async function fetchASRModes() {
    try {
      asrModes.value = await api.getASRModes()
      return asrModes.value
    } catch (e) {
      console.error('Failed to fetch ASR modes:', e)
      return null
    }
  }

  async function setASRMode(mode: ASRMode) {
    isLoading.value = true
    error.value = null
    try {
      const result = await api.setASRMode(mode)
      if (config.value) {
        config.value.asr_mode = result.mode
      }
      return result.mode
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to set ASR mode'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // Initialize all config data
  async function initialize() {
    await Promise.all([
      checkHealth(),
      fetchConfig().catch(() => null),
      fetchScenarios().catch(() => null),
      fetchWeights().catch(() => null),
      fetchASRModes()
    ])
  }

  return {
    // State
    config,
    scenarios,
    weights,
    asrModes,
    healthStatus,
    isLoading,
    error,
    // Computed
    isBackendOnline,
    currentASRMode,
    currentVideoSource,
    scenarioOptions,
    // Actions
    checkHealth,
    fetchConfig,
    updateConfig,
    fetchScenarios,
    getScenario,
    fetchWeights,
    updateWeights,
    fetchASRModes,
    setASRMode,
    initialize
  }
})
