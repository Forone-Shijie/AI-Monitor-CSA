<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import type { PoseData } from '@/types/api'

const props = withDefaults(defineProps<{
  poses: PoseData[] | null  // Multi-person support
  width?: number
  height?: number
  offsetX?: number
  offsetY?: number
  showAngles?: boolean
  maxPersons?: number
}>(), {
  width: 640,
  height: 480,
  offsetX: 0,
  offsetY: 0,
  showAngles: false,
  maxPersons: 3
})

const canvasRef = ref<HTMLCanvasElement | null>(null)

// Color palette for different persons (up to 3)
const PERSON_COLORS = [
  {
    // Person 1: Cyan (primary, matching HUD theme)
    skeleton: 'rgba(0, 212, 255, 0.6)',
    joints: '#00d4ff',
    glow: '#00d4ff40'
  },
  {
    // Person 2: Magenta/Pink
    skeleton: 'rgba(255, 0, 212, 0.6)',
    joints: '#ff00d4',
    glow: '#ff00d440'
  },
  {
    // Person 3: Lime/Green
    skeleton: 'rgba(0, 255, 136, 0.6)',
    joints: '#00ff88',
    glow: '#00ff8840'
  }
]

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

// Get angle labels for all persons
const angleLabels = computed(() => {
  const allLabels: Array<{ x: number; y: number; value: number; personIdx: number }>[] = []

  const poses = props.poses?.slice(0, props.maxPersons) || []

  for (let personIdx = 0; personIdx < poses.length; personIdx++) {
    const pose = poses[personIdx]
    if (!pose?.angles || !pose.keypoints) continue

    const angles = pose.angles
    const keypoints = pose.keypoints
    const result: Array<{ x: number; y: number; value: number; personIdx: number }> = []

    // Left elbow angle (COCO index 7)
    const leftElbow = getKeypointXY(keypoints[7])
    if (angles.left_elbow !== undefined && leftElbow) {
      result.push({
        x: leftElbow.x * props.width,
        y: leftElbow.y * props.height,
        value: Math.round(angles.left_elbow),
        personIdx
      })
    }

    // Right elbow angle (COCO index 8)
    const rightElbow = getKeypointXY(keypoints[8])
    if (angles.right_elbow !== undefined && rightElbow) {
      result.push({
        x: rightElbow.x * props.width,
        y: rightElbow.y * props.height,
        value: Math.round(angles.right_elbow),
        personIdx
      })
    }

    // Left knee angle (COCO index 13)
    const leftKnee = getKeypointXY(keypoints[13])
    if (angles.left_knee !== undefined && leftKnee) {
      result.push({
        x: leftKnee.x * props.width,
        y: leftKnee.y * props.height,
        value: Math.round(angles.left_knee),
        personIdx
      })
    }

    // Right knee angle (COCO index 14)
    const rightKnee = getKeypointXY(keypoints[14])
    if (angles.right_knee !== undefined && rightKnee) {
      result.push({
        x: rightKnee.x * props.width,
        y: rightKnee.y * props.height,
        value: Math.round(angles.right_knee),
        personIdx
      })
    }

    allLabels.push(result)
  }

  return allLabels.flat()
})

// Default color (fallback)
const DEFAULT_COLOR = PERSON_COLORS[0]!

function drawSinglePerson(
  ctx: CanvasRenderingContext2D,
  pose: PoseData,
  personIdx: number
) {
  if (!pose.keypoints) return

  const keypoints = pose.keypoints
  const colors = PERSON_COLORS[personIdx] ?? DEFAULT_COLOR

  // Draw connections
  ctx.strokeStyle = colors.skeleton
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

      // Outer glow
      ctx.beginPath()
      ctx.arc(x, y, 6, 0, Math.PI * 2)
      ctx.fillStyle = colors.glow
      ctx.fill()

      // Inner dot
      ctx.beginPath()
      ctx.arc(x, y, 3, 0, Math.PI * 2)
      ctx.fillStyle = colors.joints
      ctx.fill()
    }
  }
}

function drawSkeleton() {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // Clear canvas
  ctx.clearRect(0, 0, props.width, props.height)

  const poses = props.poses?.slice(0, props.maxPersons) || []

  // Draw each person with different colors
  for (let personIdx = 0; personIdx < poses.length; personIdx++) {
    const pose = poses[personIdx]
    if (pose?.detected && pose.keypoints) {
      drawSinglePerson(ctx, pose, personIdx)
    }
  }

  // Draw angle labels for all persons
  if (props.showAngles && angleLabels.value.length > 0) {
    ctx.font = '12px monospace'
    ctx.textAlign = 'center'

    for (const angle of angleLabels.value) {
      const colors = PERSON_COLORS[angle.personIdx] ?? DEFAULT_COLOR

      // Background
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
      ctx.fillRect(angle.x - 18, angle.y - 24, 36, 18)

      // Text with person's color
      ctx.fillStyle = colors.joints
      ctx.fillText(`${angle.value}°`, angle.x, angle.y - 10)
    }
  }
}

// Watch for changes - use timestamp of first pose or length change
watch(
  () => {
    const poses = props.poses || []
    return {
      length: poses.length,
      timestamp: poses[0]?.timestamp
    }
  },
  () => {
    drawSkeleton()
  },
  { deep: false }
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
