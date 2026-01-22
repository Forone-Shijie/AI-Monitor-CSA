/**
 * Media Devices Service - Browser WebRTC media access
 *
 * Provides browser-based camera and microphone access using getUserMedia API.
 * This replaces backend OpenCV/sounddevice which doesn't work in WSL.
 */

export interface BrowserDeviceInfo {
  deviceId: string
  label: string
  kind: 'videoinput' | 'audioinput' | 'audiooutput'
}

export interface MediaDevicesResult {
  cameras: BrowserDeviceInfo[]
  microphones: BrowserDeviceInfo[]
}

export type PermissionStatus = 'granted' | 'denied' | 'prompt'

/**
 * Request media permissions from browser
 * Must be called before enumerateDevices can return device labels
 */
export async function requestMediaPermissions(): Promise<MediaStream | null> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: true
    })
    return stream
  } catch (error) {
    console.error('Failed to request media permissions:', error)
    return null
  }
}

/**
 * Get list of available media devices
 * Note: Device labels may be empty until permissions are granted
 */
export async function getMediaDevices(): Promise<MediaDevicesResult> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()

    const cameras: BrowserDeviceInfo[] = devices
      .filter(device => device.kind === 'videoinput')
      .map((device, index) => ({
        deviceId: device.deviceId,
        label: device.label || `Camera ${index + 1}`,
        kind: device.kind as 'videoinput'
      }))

    const microphones: BrowserDeviceInfo[] = devices
      .filter(device => device.kind === 'audioinput')
      .map((device, index) => ({
        deviceId: device.deviceId,
        label: device.label || `Microphone ${index + 1}`,
        kind: device.kind as 'audioinput'
      }))

    return { cameras, microphones }
  } catch (error) {
    console.error('Failed to enumerate devices:', error)
    return { cameras: [], microphones: [] }
  }
}

/**
 * Start video capture from a specific camera
 */
export async function startVideoCapture(
  deviceId?: string,
  options?: {
    width?: number
    height?: number
    frameRate?: number
  }
): Promise<MediaStream | null> {
  try {
    const constraints: MediaStreamConstraints = {
      video: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        width: { ideal: options?.width ?? 1280 },
        height: { ideal: options?.height ?? 720 },
        frameRate: { ideal: options?.frameRate ?? 30 }
      }
    }

    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    return stream
  } catch (error) {
    console.error('Failed to start video capture:', error)
    return null
  }
}

/**
 * Start audio capture from a specific microphone
 */
export async function startAudioCapture(deviceId?: string): Promise<MediaStream | null> {
  try {
    const constraints: MediaStreamConstraints = {
      audio: {
        deviceId: deviceId ? { exact: deviceId } : undefined,
        echoCancellation: true,
        noiseSuppression: true
      }
    }

    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    return stream
  } catch (error) {
    console.error('Failed to start audio capture:', error)
    return null
  }
}

/**
 * Stop all tracks in a media stream
 */
export function stopMediaStream(stream: MediaStream | null): void {
  if (stream) {
    stream.getTracks().forEach(track => track.stop())
  }
}

/**
 * Check current permission status for camera/microphone
 */
export async function checkPermissionStatus(): Promise<{
  camera: PermissionStatus
  microphone: PermissionStatus
}> {
  const result = {
    camera: 'prompt' as PermissionStatus,
    microphone: 'prompt' as PermissionStatus
  }

  try {
    // Check camera permission
    const cameraResult = await navigator.permissions.query({ name: 'camera' as PermissionName })
    result.camera = cameraResult.state as PermissionStatus

    // Check microphone permission
    const micResult = await navigator.permissions.query({ name: 'microphone' as PermissionName })
    result.microphone = micResult.state as PermissionStatus
  } catch (error) {
    // Permissions API not supported, use 'prompt' as default
    console.warn('Permissions API not supported:', error)
  }

  return result
}

/**
 * Capture a single frame from video stream as Blob
 * @param videoElement - The video element to capture from
 * @param format - Output format ('image/jpeg' or 'image/png')
 * @param quality - JPEG quality (0-1)
 * @param maxWidth - Maximum width for scaling (0 = no scaling, keeps original resolution)
 */
export function captureVideoFrame(
  videoElement: HTMLVideoElement,
  format: 'image/jpeg' | 'image/png' = 'image/jpeg',
  quality: number = 0.8,
  maxWidth: number = 0
): Promise<Blob | null> {
  return new Promise((resolve) => {
    // Check if video dimensions are valid
    if (videoElement.videoWidth === 0 || videoElement.videoHeight === 0) {
      resolve(null)
      return
    }

    // Calculate target dimensions with optional scaling
    let targetWidth = videoElement.videoWidth
    let targetHeight = videoElement.videoHeight

    // If maxWidth is specified and video is larger, scale down proportionally
    if (maxWidth > 0 && videoElement.videoWidth > maxWidth) {
      const scale = maxWidth / videoElement.videoWidth
      targetWidth = maxWidth
      targetHeight = Math.round(videoElement.videoHeight * scale)
    }

    const canvas = document.createElement('canvas')
    canvas.width = targetWidth
    canvas.height = targetHeight

    const ctx = canvas.getContext('2d')
    if (!ctx) {
      resolve(null)
      return
    }

    // Use high-quality scaling for better visual results
    ctx.imageSmoothingEnabled = true
    ctx.imageSmoothingQuality = 'high'
    ctx.drawImage(videoElement, 0, 0, targetWidth, targetHeight)

    canvas.toBlob(
      (blob) => resolve(blob),
      format,
      quality
    )
  })
}

/**
 * Create a frame capturer that periodically captures frames
 */
export function createFrameCapturer(
  videoElement: HTMLVideoElement,
  onFrame: (blob: Blob) => void,
  fps: number = 10
): { start: () => void; stop: () => void } {
  let intervalId: number | null = null
  const interval = 1000 / fps

  return {
    start: () => {
      if (intervalId) return

      intervalId = window.setInterval(async () => {
        if (videoElement.readyState >= videoElement.HAVE_CURRENT_DATA) {
          const blob = await captureVideoFrame(videoElement)
          if (blob) {
            onFrame(blob)
          }
        }
      }, interval)
    },
    stop: () => {
      if (intervalId) {
        window.clearInterval(intervalId)
        intervalId = null
      }
    }
  }
}
