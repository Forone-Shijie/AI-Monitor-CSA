<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { PoseData } from '@/types/api'

const props = withDefaults(defineProps<{
  poseData: PoseData | null
  width?: number
  height?: number
  showAngles?: boolean
}>(), {
  width: 640,
  height: 480,
  showAngles: false
})

const canvasRef = ref<HTMLCanvasElement | null>(null)

// MediaPipe Pose connections
const connections = [
  // Face
  [0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5], [5, 6], [6, 8],
  // Torso
  [11, 12], [11, 23], [12, 24], [23, 24],
  // Left arm
  [11, 13], [13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
  // Right arm
  [12, 14], [14, 16], [16, 18], [16, 20], [16, 22], [18, 20],
  // Left leg
  [23, 25], [25, 27], [27, 29], [27, 31], [29, 31],
  // Right leg
  [24, 26], [26, 28], [28, 30], [28, 32], [30, 32]
]

const keypointColors: Record<number, string> = {
  // Face - cyan
  0: '#00d4ff', 1: '#00d4ff', 2: '#00d4ff', 3: '#00d4ff',
  4: '#00d4ff', 5: '#00d4ff', 6: '#00d4ff', 7: '#00d4ff',
  8: '#00d4ff', 9: '#00d4ff', 10: '#00d4ff',
  // Shoulders - green
  11: '#00ff88', 12: '#00ff88',
  // Arms - yellow
  13: '#ffcc00', 14: '#ffcc00', 15: '#ffcc00', 16: '#ffcc00',
  17: '#ffcc00', 18: '#ffcc00', 19: '#ffcc00', 20: '#ffcc00',
  21: '#ffcc00', 22: '#ffcc00',
  // Hips - green
  23: '#00ff88', 24: '#00ff88',
  // Legs - orange
  25: '#ff9944', 26: '#ff9944', 27: '#ff9944', 28: '#ff9944',
  29: '#ff9944', 30: '#ff9944', 31: '#ff9944', 32: '#ff9944'
}

// Helper to safely get keypoint coordinates
function getKeypointXY(kp: number[] | undefined): { x: number; y: number } | null {
  if (!kp || kp.length < 2) return null
  const x = kp[0]
  const y = kp[1]
  if (x === undefined || y === undefined) return null
  return { x, y }
}

// Helper to check keypoint visibility
function isKeypointVisible(kp: number[] | undefined, threshold = 0.5): boolean {
  if (!kp || kp.length < 3) return false
  const confidence = kp[2]
  return confidence !== undefined && confidence > threshold
}

const angleLabels = computed(() => {
  if (!props.poseData?.angles) return []
  const angles = props.poseData.angles
  const keypoints = props.poseData.keypoints || []
  const result: Array<{ x: number; y: number; value: number }> = []

  // Left elbow angle
  const kp13 = getKeypointXY(keypoints[13])
  if (angles.left_elbow !== undefined && kp13) {
    result.push({
      x: kp13.x * props.width,
      y: kp13.y * props.height,
      value: Math.round(angles.left_elbow)
    })
  }

  // Right elbow angle
  const kp14 = getKeypointXY(keypoints[14])
  if (angles.right_elbow !== undefined && kp14) {
    result.push({
      x: kp14.x * props.width,
      y: kp14.y * props.height,
      value: Math.round(angles.right_elbow)
    })
  }

  // Left knee angle
  const kp25 = getKeypointXY(keypoints[25])
  if (angles.left_knee !== undefined && kp25) {
    result.push({
      x: kp25.x * props.width,
      y: kp25.y * props.height,
      value: Math.round(angles.left_knee)
    })
  }

  // Right knee angle
  const kp26 = getKeypointXY(keypoints[26])
  if (angles.right_knee !== undefined && kp26) {
    result.push({
      x: kp26.x * props.width,
      y: kp26.y * props.height,
      value: Math.round(angles.right_knee)
    })
  }

  return result
})

function drawSkeleton() {
  const canvas = canvasRef.value
  if (!canvas || !props.poseData?.keypoints) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Clear canvas
  ctx.clearRect(0, 0, props.width, props.height)

  const keypoints = props.poseData.keypoints

  // Draw connections
  ctx.strokeStyle = 'rgba(0, 212, 255, 0.6)'
  ctx.lineWidth = 2

  for (const conn of connections) {
    const startIdx = conn[0]
    const endIdx = conn[1]
    if (startIdx === undefined || endIdx === undefined) continue

    const startKp = keypoints[startIdx]
    const endKp = keypoints[endIdx]
    const startXY = getKeypointXY(startKp)
    const endXY = getKeypointXY(endKp)

    if (startXY && endXY && isKeypointVisible(startKp) && isKeypointVisible(endKp)) {
      ctx.beginPath()
      ctx.moveTo(startXY.x * props.width, startXY.y * props.height)
      ctx.lineTo(endXY.x * props.width, endXY.y * props.height)
      ctx.stroke()
    }
  }

  // Draw keypoints
  for (let i = 0; i < keypoints.length; i++) {
    const kp = keypoints[i]
    const xy = getKeypointXY(kp)
    if (xy && isKeypointVisible(kp)) {
      const x = xy.x * props.width
      const y = xy.y * props.height
      const color = keypointColors[i as keyof typeof keypointColors] || '#00d4ff'

      // Outer glow
      ctx.beginPath()
      ctx.arc(x, y, 6, 0, Math.PI * 2)
      ctx.fillStyle = color + '40'
      ctx.fill()

      // Inner dot
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
    }
  }

  // Draw angle labels
  if (props.showAngles) {
    ctx.font = '12px monospace'
    ctx.textAlign = 'center'

    for (const angle of angleLabels.value) {
      // Background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
      ctx.fillRect(angle.x - 18, angle.y - 24, 36, 18)

      // Text
      ctx.fillStyle = '#ffcc00'
      ctx.fillText(`${angle.value}°`, angle.x, angle.y - 10)
    }
  }
}

watch(() => props.poseData, drawSkeleton, { deep: true })

onMounted(() => {
  drawSkeleton()
})
</script>

<template>
  <canvas
    ref="canvasRef"
    class="skeleton-overlay"
    :width="width"
    :height="height"
  ></canvas>
</template>

<style scoped>
.skeleton-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
}
</style>
