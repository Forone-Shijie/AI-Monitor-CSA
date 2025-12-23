<script setup lang="ts">
import { onMounted } from 'vue'
import Sidebar from './Sidebar.vue'
import { useConfigStore } from '@/stores/config'

const configStore = useConfigStore()

onMounted(async () => {
  await configStore.initialize()
})
</script>

<template>
  <div class="hud-layout">
    <Sidebar />
    <main class="hud-main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.hud-layout {
  display: flex;
  min-height: 100vh;
  background: var(--hud-bg-dark);
}

.hud-main {
  flex: 1;
  margin-left: 220px;
  min-height: 100vh;
  position: relative;
}

/* Scanline effect overlay */
.hud-main::before {
  content: '';
  position: fixed;
  top: 0;
  left: 220px;
  right: 0;
  bottom: 0;
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.03) 0px,
    rgba(0, 0, 0, 0.03) 1px,
    transparent 1px,
    transparent 2px
  );
  pointer-events: none;
  z-index: 1;
}

/* Corner decorations */
.hud-main::after {
  content: '';
  position: fixed;
  top: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  border-top: 2px solid var(--hud-border-dim);
  border-right: 2px solid var(--hud-border-dim);
  pointer-events: none;
  z-index: 10;
}

@media (max-width: 768px) {
  .hud-main {
    margin-left: 0;
  }

  .hud-main::before {
    left: 0;
  }
}
</style>
