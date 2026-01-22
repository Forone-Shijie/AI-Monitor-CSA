<script setup lang="ts">
/**
 * VideoLibrary Component
 * Display and manage uploaded videos
 */

import { computed, onMounted } from 'vue'
import { useVideoStore } from '@/stores/video'

const emit = defineEmits<{
  (e: 'select', videoId: string): void
}>()

const videoStore = useVideoStore()

const videos = computed(() => videoStore.videos)

/**
 * Format file size to human readable string
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/**
 * Format duration to mm:ss
 */
function formatDuration(seconds?: number): string {
  if (!seconds) return '--:--'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

/**
 * Format date to locale string
 */
function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

/**
 * Handle video selection
 */
function handleSelect(videoId: string) {
  videoStore.selectVideo(videoId)
  emit('select', videoId)
}

/**
 * Handle video deletion
 */
async function handleDelete(videoId: string, e: Event) {
  e.stopPropagation()

  if (confirm('确定要删除此视频吗？')) {
    await videoStore.deleteVideo(videoId)
  }
}

// Fetch videos on mount
onMounted(() => {
  videoStore.fetchVideos()
})
</script>

<template>
  <div class="video-library">
    <!-- Loading State -->
    <div v-if="videoStore.isLoading" class="library-loading">
      <span>加载中...</span>
    </div>

    <!-- Empty State -->
    <div v-else-if="videos.length === 0" class="library-empty">
      <p>暂无上传的视频</p>
    </div>

    <!-- Video List -->
    <div v-else class="video-list">
      <div
        v-for="video in videos"
        :key="video.video_id"
        class="video-item"
        :class="{ selected: video.video_id === videoStore.selectedVideoId }"
        @click="handleSelect(video.video_id)"
      >
        <!-- Video Thumbnail / Format Badge -->
        <div class="video-thumbnail">
          <span class="format-badge">{{ video.format.toUpperCase() }}</span>
        </div>

        <!-- Video Info -->
        <div class="video-info">
          <span class="video-name" :title="video.original_filename">
            {{ video.original_filename }}
          </span>
          <div class="video-meta">
            <span class="meta-item">
              <svg viewBox="0 0 24 24" fill="currentColor" width="12" height="12">
                <path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10 10-4.5 10-10S17.5 2 12 2zm4.2 14.2L11 13V7h1.5v5.2l4.5 2.7-.8 1.3z"/>
              </svg>
              {{ formatDuration(video.duration) }}
            </span>
            <span class="meta-item">{{ formatFileSize(video.file_size) }}</span>
            <span class="meta-item meta-date">{{ formatDate(video.uploaded_at) }}</span>
          </div>
          <div class="video-resolution" v-if="video.width && video.height">
            {{ video.width }}x{{ video.height }} @ {{ video.fps?.toFixed(0) }}fps
          </div>
        </div>

        <!-- Delete Button -->
        <button
          class="delete-btn"
          @click="handleDelete(video.video_id, $event)"
          title="删除视频"
        >
          <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.video-library {
  max-height: 240px;
  overflow-y: auto;
}

.library-loading,
.library-empty {
  text-align: center;
  color: var(--hud-text-muted);
  padding: var(--hud-spacing-lg);
  font-size: 13px;
}

.video-list {
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-sm);
}

.video-item {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
  padding: var(--hud-spacing-sm) var(--hud-spacing-md);
  background: var(--hud-bg-light);
  border: 1px solid transparent;
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  transition: var(--hud-transition);
}

.video-item:hover {
  border-color: var(--hud-border-dim);
}

.video-item.selected {
  border-color: var(--hud-border);
  background: rgba(0, 212, 255, 0.1);
}

.video-thumbnail {
  width: 48px;
  height: 36px;
  background: var(--hud-bg);
  border-radius: var(--hud-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.format-badge {
  font-size: 10px;
  font-family: var(--font-mono);
  color: var(--hud-border);
  font-weight: 600;
}

.video-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.video-name {
  font-size: 13px;
  color: var(--hud-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.video-meta {
  display: flex;
  gap: var(--hud-spacing-md);
  font-size: 11px;
  color: var(--hud-text-muted);
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 2px;
}

.meta-item svg {
  opacity: 0.7;
}

.meta-date {
  font-family: var(--font-mono);
}

.video-resolution {
  font-size: 10px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

.delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--hud-radius-sm);
  cursor: pointer;
  color: var(--hud-text-muted);
  transition: var(--hud-transition);
  flex-shrink: 0;
}

.delete-btn:hover {
  border-color: var(--hud-danger);
  color: var(--hud-danger);
  background: rgba(255, 68, 68, 0.1);
}
</style>
