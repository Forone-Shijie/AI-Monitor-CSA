/**
 * Media Store - Pinia store for browser media device management
 *
 * Manages WebRTC media streams, device selection, and permissions.
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { BrowserDeviceInfo, PermissionStatus } from '@/services/mediaDevices'
import * as mediaDevices from '@/services/mediaDevices'

export const useMediaStore = defineStore('media', () => {
  // State
  const cameras = ref<BrowserDeviceInfo[]>([])
  const microphones = ref<BrowserDeviceInfo[]>([])
  const selectedCameraId = ref<string | null>(null)
  const selectedMicrophoneId = ref<string | null>(null)
  const videoStream = ref<MediaStream | null>(null)
  const audioStream = ref<MediaStream | null>(null)
  const cameraPermission = ref<PermissionStatus>('prompt')
  const microphonePermission = ref<PermissionStatus>('prompt')
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // Computed
  const hasCameras = computed(() => cameras.value.length > 0)
  const hasMicrophones = computed(() => microphones.value.length > 0)
  const hasVideoStream = computed(() => videoStream.value !== null)
  const hasAudioStream = computed(() => audioStream.value !== null)
  const isPermissionGranted = computed(() =>
    cameraPermission.value === 'granted' || microphonePermission.value === 'granted'
  )

  const cameraOptions = computed(() =>
    cameras.value.map(c => ({
      value: c.deviceId,
      label: c.label
    }))
  )

  const microphoneOptions = computed(() =>
    microphones.value.map(m => ({
      value: m.deviceId,
      label: m.label
    }))
  )

  // Actions
  async function requestPermissions(): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      const stream = await mediaDevices.requestMediaPermissions()
      if (stream) {
        // Stop the temporary stream - we just needed permissions
        mediaDevices.stopMediaStream(stream)

        // Update permission status
        const status = await mediaDevices.checkPermissionStatus()
        cameraPermission.value = status.camera
        microphonePermission.value = status.microphone

        // Refresh device list with labels
        await refreshDevices()
        return true
      }
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to request permissions'
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function refreshDevices(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const devices = await mediaDevices.getMediaDevices()
      cameras.value = devices.cameras
      microphones.value = devices.microphones

      // Set default selections if not already set
      const firstCamera = devices.cameras[0]
      const firstMic = devices.microphones[0]
      if (!selectedCameraId.value && firstCamera) {
        selectedCameraId.value = firstCamera.deviceId
      }
      if (!selectedMicrophoneId.value && firstMic) {
        selectedMicrophoneId.value = firstMic.deviceId
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to get devices'
    } finally {
      isLoading.value = false
    }
  }

  async function checkPermissions(): Promise<void> {
    try {
      const status = await mediaDevices.checkPermissionStatus()
      cameraPermission.value = status.camera
      microphonePermission.value = status.microphone
    } catch (e) {
      console.error('Failed to check permissions:', e)
    }
  }

  async function startVideo(deviceId?: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      // Stop existing stream
      if (videoStream.value) {
        mediaDevices.stopMediaStream(videoStream.value)
      }

      const stream = await mediaDevices.startVideoCapture(deviceId || selectedCameraId.value || undefined)
      if (stream) {
        videoStream.value = stream
        if (deviceId) {
          selectedCameraId.value = deviceId
        }
        return true
      }
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start video'
      return false
    } finally {
      isLoading.value = false
    }
  }

  async function startAudio(deviceId?: string): Promise<boolean> {
    isLoading.value = true
    error.value = null

    try {
      // Stop existing stream
      if (audioStream.value) {
        mediaDevices.stopMediaStream(audioStream.value)
      }

      const stream = await mediaDevices.startAudioCapture(deviceId || selectedMicrophoneId.value || undefined)
      if (stream) {
        audioStream.value = stream
        if (deviceId) {
          selectedMicrophoneId.value = deviceId
        }
        return true
      }
      return false
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to start audio'
      return false
    } finally {
      isLoading.value = false
    }
  }

  function stopVideo(): void {
    if (videoStream.value) {
      mediaDevices.stopMediaStream(videoStream.value)
      videoStream.value = null
    }
  }

  function stopAudio(): void {
    if (audioStream.value) {
      mediaDevices.stopMediaStream(audioStream.value)
      audioStream.value = null
    }
  }

  function stopAllStreams(): void {
    stopVideo()
    stopAudio()
  }

  function selectCamera(deviceId: string): void {
    selectedCameraId.value = deviceId
  }

  function selectMicrophone(deviceId: string): void {
    selectedMicrophoneId.value = deviceId
  }

  // Initialize
  async function initialize(): Promise<void> {
    await checkPermissions()
    await refreshDevices()
  }

  // Cleanup on store reset
  function $reset(): void {
    stopAllStreams()
    cameras.value = []
    microphones.value = []
    selectedCameraId.value = null
    selectedMicrophoneId.value = null
    cameraPermission.value = 'prompt'
    microphonePermission.value = 'prompt'
    error.value = null
  }

  return {
    // State
    cameras,
    microphones,
    selectedCameraId,
    selectedMicrophoneId,
    videoStream,
    audioStream,
    cameraPermission,
    microphonePermission,
    isLoading,
    error,
    // Computed
    hasCameras,
    hasMicrophones,
    hasVideoStream,
    hasAudioStream,
    isPermissionGranted,
    cameraOptions,
    microphoneOptions,
    // Actions
    requestPermissions,
    refreshDevices,
    checkPermissions,
    startVideo,
    startAudio,
    stopVideo,
    stopAudio,
    stopAllStreams,
    selectCamera,
    selectMicrophone,
    initialize,
    $reset
  }
})
