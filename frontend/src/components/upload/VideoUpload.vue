<script setup lang="ts">
/**
 * VideoUpload Component
 * Drag-and-drop video upload with progress display
 */

import { ref } from 'vue'
import { useVideoStore } from '@/stores/video'

const emit = defineEmits<{
  (e: 'uploaded', videoId: string): void
  (e: 'error', message: string): void
}>()

const videoStore = useVideoStore()

// State
const isDragOver = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)

// Constants
const MAX_SIZE = 500 * 1024 * 1024 // 500MB
const ALLOWED_TYPES = [
  'video/mp4',
  'video/avi',
  'video/x-msvideo',
  'video/quicktime',
  'video/webm',
  'video/x-matroska'
]
const ALLOWED_EXTENSIONS = ['.mp4', '.avi', '.mkv', '.mov', '.webm']

/**
 * Validate and handle file upload
 */
async function handleFile(file: File) {
  // Validate file type
  const ext = '.' + file.name.split('.').pop()?.toLowerCase()
  const isValidType = ALLOWED_TYPES.includes(file.type) || ALLOWED_EXTENSIONS.includes(ext)

  if (!isValidType) {
    const error = `不支持的文件格式，请上传 ${ALLOWED_EXTENSIONS.join('/')} 格式视频`
    emit('error', error)
    return
  }

  // Validate file size
  if (file.size > MAX_SIZE) {
    const error = `文件过大，最大支持 ${MAX_SIZE / (1024 * 1024)}MB`
    emit('error', error)
    return
  }

  // Upload
  const video = await videoStore.uploadVideo(file)
  if (video) {
    emit('uploaded', video.video_id)
  } else if (videoStore.error) {
    emit('error', videoStore.error)
  }
}

/**
 * Handle drag over event
 */
function handleDragOver(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = true
}

/**
 * Handle drag leave event
 */
function handleDragLeave() {
  isDragOver.value = false
}

/**
 * Handle drop event
 */
function handleDrop(e: DragEvent) {
  e.preventDefault()
  isDragOver.value = false

  const file = e.dataTransfer?.files[0]
  if (file) {
    handleFile(file)
  }
}

/**
 * Handle file input change
 */
function handleFileSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    handleFile(file)
  }
  // Reset input to allow selecting the same file again
  target.value = ''
}

/**
 * Trigger file input click
 */
function triggerFileSelect() {
  fileInput.value?.click()
}
</script>

<template>
  <div
    class="upload-zone"
    :class="{ 'drag-over': isDragOver, 'is-uploading': videoStore.isLoading }"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
    @click="triggerFileSelect"
  >
    <input
      ref="fileInput"
      type="file"
      accept="video/*,.mp4,.avi,.mkv,.mov,.webm"
      hidden
      @change="handleFileSelect"
    />

    <!-- Upload Icon & Text -->
    <div class="upload-content" v-if="!videoStore.isLoading">
      <div class="upload-icon">
        <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
          <path d="M9 16h6v-6h4l-7-7-7 7h4v6zm-4 2h14v2H5v-2z"/>
        </svg>
      </div>
      <p class="upload-text">点击或拖拽视频文件到此处上传</p>
      <p class="upload-hint">支持 MP4/AVI/MKV/MOV/WEBM，最大 500MB</p>
    </div>

    <!-- Upload Progress -->
    <div class="upload-progress" v-else>
      <div class="progress-bar">
        <div
          class="progress-fill"
          :style="{ width: `${videoStore.uploadProgress}%` }"
        ></div>
      </div>
      <p class="progress-text">上传中... {{ videoStore.uploadProgress }}%</p>
    </div>
  </div>
</template>

<style scoped>
.upload-zone {
  border: 2px dashed var(--hud-border-dim);
  border-radius: var(--hud-radius-md);
  padding: var(--hud-spacing-xl);
  text-align: center;
  cursor: pointer;
  transition: var(--hud-transition);
  background: var(--hud-bg-light);
}

.upload-zone:hover,
.upload-zone.drag-over {
  border-color: var(--hud-border);
  background: rgba(0, 212, 255, 0.05);
  box-shadow: var(--hud-glow);
}

.upload-zone.is-uploading {
  cursor: default;
  pointer-events: none;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hud-spacing-sm);
}

.upload-icon {
  color: var(--hud-border);
  opacity: 0.8;
}

.upload-text {
  font-size: 14px;
  color: var(--hud-text-primary);
  margin: 0;
}

.upload-hint {
  font-size: 12px;
  color: var(--hud-text-muted);
  margin: 0;
}

.upload-progress {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--hud-spacing-md);
  width: 100%;
}

.progress-bar {
  width: 100%;
  max-width: 300px;
  height: 8px;
  background: var(--hud-bg);
  border-radius: 4px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--hud-border);
  border-radius: 4px;
  transition: width 0.2s ease;
}

.progress-text {
  font-size: 14px;
  color: var(--hud-text-primary);
  font-family: var(--font-mono);
  margin: 0;
}
</style>
