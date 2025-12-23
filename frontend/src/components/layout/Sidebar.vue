<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useConfigStore } from '@/stores/config'

const route = useRoute()
const router = useRouter()
const configStore = useConfigStore()

const navItems = [
  { path: '/', name: 'Dashboard', icon: 'dashboard', label: '仪表盘' },
  { path: '/live', name: 'LiveMonitor', icon: 'monitor', label: '实时监控' },
  { path: '/playback', name: 'PlaybackAnalysis', icon: 'playback', label: '录像分析' },
  { path: '/reports', name: 'Reports', icon: 'report', label: '评估报告' }
]

// SVG icon paths for each nav item
const iconPaths: Record<string, string> = {
  dashboard: 'M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z',
  monitor: 'M21 3H3c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h5v2h8v-2h5c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 14H3V5h18v12z',
  playback: 'M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z',
  report: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z'
}

const currentPath = computed(() => route.path)

const statusClass = computed(() => {
  if (configStore.isBackendOnline) return 'status--online'
  return 'status--offline'
})

const statusText = computed(() => {
  if (configStore.isBackendOnline) return '系统在线'
  return '系统离线'
})

function navigate(path: string) {
  router.push(path)
}
</script>

<template>
  <aside class="sidebar">
    <!-- Logo -->
    <div class="sidebar-logo">
      <div class="logo-icon">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
        </svg>
      </div>
      <div class="logo-text">
        <span class="logo-title">乘务监测</span>
        <span class="logo-subtitle">系统</span>
      </div>
    </div>

    <!-- Navigation -->
    <nav class="sidebar-nav">
      <button
        v-for="item in navItems"
        :key="item.path"
        class="nav-item"
        :class="{ 'nav-item--active': currentPath === item.path }"
        @click="navigate(item.path)"
      >
        <span class="nav-icon">
          <svg viewBox="0 0 24 24" fill="currentColor" class="nav-svg">
            <path :d="iconPaths[item.icon]" />
          </svg>
        </span>
        <span class="nav-label">{{ item.label }}</span>
        <span class="nav-indicator" v-if="currentPath === item.path"></span>
      </button>
    </nav>

    <!-- System Status -->
    <div class="sidebar-footer">
      <div class="system-status" :class="statusClass">
        <span class="status-dot"></span>
        <span class="status-text">{{ statusText }}</span>
      </div>
      <div class="version-info">
        <span>v1.0.0</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 220px;
  height: 100vh;
  background: var(--hud-bg);
  border-right: 1px solid var(--hud-border-dim);
  display: flex;
  flex-direction: column;
  position: fixed;
  left: 0;
  top: 0;
  z-index: 100;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
  padding: var(--hud-spacing-lg);
  border-bottom: 1px solid var(--hud-border-dim);
}

.logo-icon {
  width: 40px;
  height: 40px;
  color: var(--hud-border);
  filter: drop-shadow(0 0 8px rgba(0, 212, 255, 0.5));
}

.logo-icon svg {
  width: 100%;
  height: 100%;
}

.logo-text {
  display: flex;
  flex-direction: column;
}

.logo-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--hud-border);
  letter-spacing: 2px;
}

.logo-subtitle {
  font-size: 12px;
  color: var(--hud-text-secondary);
  letter-spacing: 1px;
}

.sidebar-nav {
  flex: 1;
  padding: var(--hud-spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--hud-spacing-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-md);
  padding: var(--hud-spacing-md);
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--hud-radius-md);
  color: var(--hud-text-secondary);
  cursor: pointer;
  transition: var(--hud-transition);
  position: relative;
  text-align: left;
  width: 100%;
}

.nav-item:hover {
  background: rgba(0, 212, 255, 0.05);
  border-color: var(--hud-border-dim);
  color: var(--hud-text-primary);
}

.nav-item--active {
  background: rgba(0, 212, 255, 0.1);
  border-color: var(--hud-border);
  color: var(--hud-border);
  box-shadow: var(--hud-glow);
}

.nav-icon {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.nav-svg {
  width: 20px;
  height: 20px;
}

.nav-label {
  font-size: 14px;
  font-weight: 500;
}

.nav-indicator {
  position: absolute;
  right: -1px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 24px;
  background: var(--hud-border);
  border-radius: 2px 0 0 2px;
  box-shadow: 0 0 10px var(--hud-border);
}

.sidebar-footer {
  padding: var(--hud-spacing-md);
  border-top: 1px solid var(--hud-border-dim);
}

.system-status {
  display: flex;
  align-items: center;
  gap: var(--hud-spacing-sm);
  font-size: 12px;
  margin-bottom: var(--hud-spacing-sm);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

.status--online .status-dot {
  background: var(--hud-success);
  box-shadow: 0 0 8px var(--hud-success);
}

.status--online .status-text {
  color: var(--hud-success);
}

.status--offline .status-dot {
  background: var(--hud-danger);
  box-shadow: 0 0 8px var(--hud-danger);
}

.status--offline .status-text {
  color: var(--hud-danger);
}

.version-info {
  font-size: 11px;
  color: var(--hud-text-muted);
  font-family: var(--font-mono);
}

</style>
