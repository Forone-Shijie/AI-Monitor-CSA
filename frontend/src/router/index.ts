import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Dashboard',
    component: () => import('@/views/Dashboard.vue'),
    meta: { title: '仪表盘' }
  },
  {
    path: '/live',
    name: 'LiveMonitor',
    component: () => import('@/views/LiveMonitor.vue'),
    meta: { title: '实时监控' }
  },
  {
    path: '/playback',
    name: 'PlaybackAnalysis',
    component: () => import('@/views/PlaybackAnalysis.vue'),
    meta: { title: '录像分析' }
  },
  {
    path: '/reports',
    name: 'Reports',
    component: () => import('@/views/Reports.vue'),
    meta: { title: '评估报告' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard for page title
router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || '乘务监测系统'} - 乘务监测系统`
  next()
})

export default router
