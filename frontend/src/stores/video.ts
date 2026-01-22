/**
 * Video Store - Manages uploaded video files
 *
 * Provides state and actions for:
 * - Uploading videos
 * - Listing videos
 * - Selecting videos for analysis
 * - Deleting videos
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { VideoInfo } from '@/types/api'
import * as api from '@/services/api'

export const useVideoStore = defineStore('video', () => {
  // ==========================================================================
  // State
  // ==========================================================================

  /** List of uploaded videos */
  const videos = ref<VideoInfo[]>([])

  /** Currently selected video ID */
  const selectedVideoId = ref<string | null>(null)

  /** Loading state */
  const isLoading = ref(false)

  /** Upload progress (0-100) */
  const uploadProgress = ref(0)

  /** Error message */
  const error = ref<string | null>(null)

  // ==========================================================================
  // Computed
  // ==========================================================================

  /** Get the currently selected video */
  const selectedVideo = computed(() =>
    videos.value.find(v => v.video_id === selectedVideoId.value) || null
  )

  /** Check if any video is selected */
  const hasSelectedVideo = computed(() => selectedVideoId.value !== null)

  /** Total number of videos */
  const totalVideos = computed(() => videos.value.length)

  // ==========================================================================
  // Actions
  // ==========================================================================

  /**
   * Fetch all uploaded videos from server.
   */
  async function fetchVideos(): Promise<void> {
    isLoading.value = true
    error.value = null

    try {
      const response = await api.listVideos()
      videos.value = response.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to fetch videos'
      console.error('Failed to fetch videos:', e)
    } finally {
      isLoading.value = false
    }
  }

  /**
   * Upload a video file.
   * @param file - Video file to upload
   * @returns Uploaded video info or null on failure
   */
  async function uploadVideo(file: File): Promise<VideoInfo | null> {
    isLoading.value = true
    uploadProgress.value = 0
    error.value = null

    try {
      const response = await api.uploadVideo(file, (progress) => {
        uploadProgress.value = progress
      })

      if (response.success) {
        // Add to list (at the beginning)
        videos.value.unshift(response.data)
        // Auto-select the uploaded video
        selectedVideoId.value = response.data.video_id
        return response.data
      }

      error.value = response.message || 'Upload failed'
      return null
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Upload failed'
      console.error('Failed to upload video:', e)
      return null
    } finally {
      isLoading.value = false
      uploadProgress.value = 0
    }
  }

  /**
   * Delete an uploaded video.
   * @param videoId - Video ID to delete
   */
  async function deleteVideo(videoId: string): Promise<boolean> {
    try {
      await api.deleteVideo(videoId)

      // Remove from list
      videos.value = videos.value.filter(v => v.video_id !== videoId)

      // Clear selection if deleted video was selected
      if (selectedVideoId.value === videoId) {
        selectedVideoId.value = null
      }

      return true
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Delete failed'
      console.error('Failed to delete video:', e)
      return false
    }
  }

  /**
   * Select a video by ID.
   * @param videoId - Video ID to select
   */
  function selectVideo(videoId: string | null): void {
    selectedVideoId.value = videoId
  }

  /**
   * Get video stream URL for playback.
   * @param videoId - Video ID
   */
  function getStreamUrl(videoId: string): string {
    return api.getVideoStreamUrl(videoId)
  }

  /**
   * Clear error message.
   */
  function clearError(): void {
    error.value = null
  }

  /**
   * Reset store state.
   */
  function reset(): void {
    videos.value = []
    selectedVideoId.value = null
    isLoading.value = false
    uploadProgress.value = 0
    error.value = null
  }

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    videos,
    selectedVideoId,
    isLoading,
    uploadProgress,
    error,

    // Computed
    selectedVideo,
    hasSelectedVideo,
    totalVideos,

    // Actions
    fetchVideos,
    uploadVideo,
    deleteVideo,
    selectVideo,
    getStreamUrl,
    clearError,
    reset
  }
})
