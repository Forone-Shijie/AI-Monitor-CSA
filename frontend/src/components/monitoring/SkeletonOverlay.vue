<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { PoseData } from '@/types/api'

const props = withDefaults(defineProps<{
  poseData: PoseData | null
  width?: number
  height?: number
  offsetX?: number
  offsetY?: number
  showAngles?: boolean
}>(), {
  width: 640,
  height: 480,
  offsetX: 0,
  offsetY: 0,
  showAngles: false
})

const canvasRef = ref<HTMLCanvasElement | null>(null)

// COCO 17-point Pose connections (RTMPose output format)
// Keypoint indices:
//   0: Nose, 1: Left Eye, 2: Right Eye, 3: Left Ear, 4: Right Ear
//   5: Left Shoulder, 6: Right Shoulder, 7: Left Elbow, 8: Right Elbow
//   9: Left Wrist, 10: Right Wrist, 11: Left Hip, 12: Right Hip
//   13: Left Knee, 14: Right Knee, 15: Left Ankle, 16: Right Ankle
const connections = [
  // Head
  [0, 1], [0, 2],       // Nose to eyes
  [1, 3], [2, 4],       // Eyes to ears
  // Upper body - shoulders
  [5, 6],               // Left shoulder to right shoulder
  // Left arm
  [5, 7], [7, 9],       // Shoulder to elbow to wrist
  // Right arm
  [6, 8], [8, 10],      // Shoulder to elbow to wrist
  // Torso
  [5, 11], [6, 12],     // Shoulders to hips
  [11, 12],             // Left hip to right hip
  // Left leg
  [11, 13], [13, 15],   // Hip to knee to ankle
  // Right leg
  [12, 14], [14, 16],   // Hip to knee to ankle
]

const keypointColors: Record<number, string> = {
  // Face - cyan
  0: '#00d4ff',   // Nose
  1: '#00d4ff',   // Left Eye
  2: '#00d4ff',   // Right Eye
  3: '#00d4ff',   // Left Ear
  4: '#00d4ff',   // Right Ear
  // Shoulders - green
  5: '#00ff88',   // Left Shoulder
  6: '#00ff88',   // Right Shoulder
  // Arms - yellow
  7: '#ffcc00',   // Left Elbow
  8: '#ffcc00',   // Right Elbow
  9: '#ffcc00',   // Left Wrist
  10: '#ffcc00',  // Right Wrist
  // Hips - green
  11: '#00ff88',  // Left Hip
  12: '#00ff88',  // Right Hip
  // Legs - orange
  13: '#ff9944',  // Left Knee
  14: '#ff9944',  // Right Knee
  15: '#ff9944',  // Left Ankle
  16: '#ff9944',  // Right Ankle
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
// MediaPipe keypoints: [x, y, z, visibility] - visibility is at index 3
function isKeypointVisible(kp: number[] | undefined, threshold = 0.5): boolean {
  if (!kp || kp.length < 4) return false
  const visibility = kp[3]  // visibility is the 4th element, not z (which is at index 2)
  return visibility !== undefined && visibility > threshold
}

const angleLabels = computed(() => {
  if (!props.poseData?.angles) return []
  const angles = props.poseData.angles
  const keypoints = props.poseData.keypoints || []
  const result: Array<{ x: number; y: number; value: number }> = []

  // Left elbow angle (COCO index 7)
  const leftElbow = getKeypointXY(keypoints[7])
  if (angles.left_elbow !== undefined && leftElbow) {
    result.push({
      x: leftElbow.x * props.width,
      y: leftElbow.y * props.height,
      value: Math.round(angles.left_elbow)
    })
  }

  // Right elbow angle (COCO index 8)
  const rightElbow = getKeypointXY(keypoints[8])
  if (angles.right_elbow !== undefined && rightElbow) {
    result.push({
      x: rightElbow.x * props.width,
      y: rightElbow.y * props.height,
      value: Math.round(angles.right_elbow)
    })
  }

  // Left knee angle (COCO index 13)
  const leftKnee = getKeypointXY(keypoints[13])
  if (angles.left_knee !== undefined && leftKnee) {
    result.push({
      x: leftKnee.x * props.width,
      y: leftKnee.y * props.height,
      value: Math.round(angles.left_knee)
    })
  }

  // Right knee angle (COCO index 14)
  const rightKnee = getKeypointXY(keypoints[14])
  if (angles.right_knee !== undefined && rightKnee) {
    result.push({
      x: rightKnee.x * props.width,
      y: rightKnee.y * props.height,
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

// Watch only timestamp to avoid expensive deep comparison
watch(
  () => props.poseData?.timestamp,
  () => {
    if (props.poseData) drawSkeleton()
  }
)

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
    :style="{ left: `${offsetX}px`, top: `${offsetY}px` }"
  ></canvas>
</template>

<style scoped>
.skeleton-overlay {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: none;
  z-index: 3;
}
</style>
