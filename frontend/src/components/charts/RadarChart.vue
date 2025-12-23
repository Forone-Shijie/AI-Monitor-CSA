<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import type { ScoreBreakdown } from '@/types/api'

const props = withDefaults(defineProps<{
  scores: ScoreBreakdown | null
  width?: string
  height?: string
}>(), {
  width: '100%',
  height: '300px'
})

const chartRef = ref<HTMLDivElement | null>(null)
let chartInstance: echarts.ECharts | null = null

const chartData = computed(() => {
  if (!props.scores) {
    return [0, 0, 0]
  }
  return [
    props.scores.pose.score,
    props.scores.action.score,
    props.scores.communication.score
  ]
})

function initChart() {
  if (!chartRef.value) return

  chartInstance = echarts.init(chartRef.value, 'dark')

  const option: echarts.EChartsOption = {
    backgroundColor: 'transparent',
    radar: {
      indicator: [
        { name: '姿态标准', max: 100 },
        { name: '动作时效', max: 100 },
        { name: '沟通协同', max: 100 }
      ],
      center: ['50%', '50%'],
      radius: '65%',
      startAngle: 90,
      splitNumber: 4,
      shape: 'polygon',
      axisName: {
        color: 'rgba(255, 255, 255, 0.7)',
        fontSize: 12,
        fontFamily: 'Microsoft YaHei'
      },
      splitArea: {
        areaStyle: {
          color: [
            'rgba(0, 212, 255, 0.05)',
            'rgba(0, 212, 255, 0.1)',
            'rgba(0, 212, 255, 0.15)',
            'rgba(0, 212, 255, 0.2)'
          ]
        }
      },
      axisLine: {
        lineStyle: {
          color: 'rgba(0, 212, 255, 0.3)'
        }
      },
      splitLine: {
        lineStyle: {
          color: 'rgba(0, 212, 255, 0.3)'
        }
      }
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: chartData.value,
            name: '评分',
            symbol: 'circle',
            symbolSize: 8,
            lineStyle: {
              color: '#00d4ff',
              width: 2
            },
            areaStyle: {
              color: new echarts.graphic.RadialGradient(0.5, 0.5, 1, [
                { offset: 0, color: 'rgba(0, 212, 255, 0.4)' },
                { offset: 1, color: 'rgba(0, 212, 255, 0.1)' }
              ])
            },
            itemStyle: {
              color: '#00d4ff',
              borderColor: '#00d4ff',
              borderWidth: 2
            }
          }
        ]
      }
    ],
    animation: true,
    animationDuration: 500
  }

  chartInstance.setOption(option)
}

function updateChart() {
  if (!chartInstance) return

  chartInstance.setOption({
    series: [
      {
        data: [
          {
            value: chartData.value,
            name: '评分'
          }
        ]
      }
    ]
  })
}

function handleResize() {
  chartInstance?.resize()
}

watch(() => props.scores, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<template>
  <div
    ref="chartRef"
    class="radar-chart"
    :style="{ width, height }"
  ></div>
</template>

<style scoped>
.radar-chart {
  min-height: 200px;
}
</style>
