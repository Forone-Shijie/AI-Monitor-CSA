"""
Video Manager - Handles uploaded video file lifecycle.

Responsibilities:
- File storage and retrieval
- Metadata extraction using OpenCV
- File cleanup and deletion
"""

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import cv2

logger = logging.getLogger(__name__)


class VideoInfo:
    """Video file information."""

    def __init__(
        self,
        video_id: str,
        original_filename: str,
        file_path: str,
        file_size: int,
        format: str,
        uploaded_at: datetime,
        duration: Optional[float] = None,
        width: Optional[int] = None,
        height: Optional[int] = None,
        fps: Optional[float] = None,
    ):
        self.video_id = video_id
        self.original_filename = original_filename
        self.file_path = file_path
        self.file_size = file_size
        self.format = format
        self.uploaded_at = uploaded_at
        self.duration = duration
        self.width = width
        self.height = height
        self.fps = fps

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "video_id": self.video_id,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "format": self.format,
            "uploaded_at": self.uploaded_at.isoformat(),
            "duration": self.duration,
            "width": self.width,
            "height": self.height,
            "fps": self.fps,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "VideoInfo":
        """Create from dictionary."""
        uploaded_at = data.get("uploaded_at")
        if isinstance(uploaded_at, str):
            uploaded_at = datetime.fromisoformat(uploaded_at)
        elif uploaded_at is None:
            uploaded_at = datetime.now()

        return cls(
            video_id=data["video_id"],
            original_filename=data["original_filename"],
            file_path=data["file_path"],
            file_size=data["file_size"],
            format=data["format"],
            uploaded_at=uploaded_at,
            duration=data.get("duration"),
            width=data.get("width"),
            height=data.get("height"),
            fps=data.get("fps"),
        )


class VideoManager:
    """Manages uploaded video files."""

    # Allowed video extensions
    ALLOWED_EXTENSIONS = {".mp4", ".avi", ".mkv", ".mov", ".webm"}

    # Maximum file size (500MB)
    MAX_FILE_SIZE = 500 * 1024 * 1024

    def __init__(self, upload_dir: str = "uploads/videos"):
        """
        Initialize VideoManager.

        Args:
            upload_dir: Directory for storing uploaded videos
        """
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        # Metadata storage
        self._metadata_file = self.upload_dir / "metadata.json"
        self._videos: Dict[str, VideoInfo] = {}

        # Load existing videos on startup
        self._load_metadata()

        logger.info(f"VideoManager initialized. Upload dir: {self.upload_dir}")

    def _load_metadata(self) -> None:
        """Load metadata for existing videos."""
        if self._metadata_file.exists():
            try:
                with open(self._metadata_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for video_data in data.get("videos", []):
                        video_info = VideoInfo.from_dict(video_data)
                        # Verify file still exists
                        if Path(video_info.file_path).exists():
                            self._videos[video_info.video_id] = video_info
                        else:
                            logger.warning(
                                f"Video file not found: {video_info.file_path}"
                            )
                logger.info(f"Loaded {len(self._videos)} existing videos")
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

    def _save_metadata(self) -> None:
        """Save metadata to file."""
        try:
            data = {"videos": [v.to_dict() for v in self._videos.values()]}
            with open(self._metadata_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")

    def generate_video_id(self) -> str:
        """Generate unique video ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique = uuid.uuid4().hex[:8]
        return f"vid_{timestamp}_{unique}"

    def validate_file(self, filename: str, file_size: int) -> Optional[str]:
        """
        Validate uploaded file.

        Args:
            filename: Original filename
            file_size: File size in bytes

        Returns:
            Error message if validation fails, None if valid
        """
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return f"Unsupported format: {ext}. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"

        # Check size
        if file_size > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            return f"File too large. Maximum size: {max_mb:.0f}MB"

        return None

    def extract_metadata(self, file_path: Path) -> Dict:
        """
        Extract video metadata using OpenCV.

        Args:
            file_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        metadata = {
            "width": None,
            "height": None,
            "fps": None,
            "duration": None,
        }

        cap = cv2.VideoCapture(str(file_path))
        try:
            if cap.isOpened():
                metadata["width"] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                metadata["height"] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                metadata["fps"] = cap.get(cv2.CAP_PROP_FPS)

                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                if metadata["fps"] and metadata["fps"] > 0:
                    metadata["duration"] = frame_count / metadata["fps"]

                logger.debug(
                    f"Extracted metadata: {metadata['width']}x{metadata['height']} "
                    f"@ {metadata['fps']:.2f}fps, duration: {metadata['duration']:.2f}s"
                )
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
        finally:
            cap.release()

        return metadata

    async def save_video(
        self,
        file_content: bytes,
        original_filename: str,
    ) -> VideoInfo:
        """
        Save uploaded video and extract metadata.

        Args:
            file_content: Video file bytes
            original_filename: Original filename from upload

        Returns:
            VideoInfo with metadata
        """
        # Generate video ID
        video_id = self.generate_video_id()

        # Get extension
        ext = Path(original_filename).suffix.lower()

        # Build file path
        file_path = self.upload_dir / f"{video_id}{ext}"

        # Save file
        with open(file_path, "wb") as f:
            f.write(file_content)

        logger.info(f"Saved video: {file_path} ({len(file_content)} bytes)")

        # Extract metadata
        metadata = self.extract_metadata(file_path)

        # Create VideoInfo
        video_info = VideoInfo(
            video_id=video_id,
            original_filename=original_filename,
            file_path=str(file_path),
            file_size=len(file_content),
            format=ext.lstrip("."),
            uploaded_at=datetime.now(),
            width=metadata.get("width"),
            height=metadata.get("height"),
            fps=metadata.get("fps"),
            duration=metadata.get("duration"),
        )

        # Store in memory
        self._videos[video_id] = video_info

        # Persist metadata
        self._save_metadata()

        return video_info

    def get_video(self, video_id: str) -> Optional[VideoInfo]:
        """Get video info by ID."""
        return self._videos.get(video_id)

    def list_videos(self) -> List[VideoInfo]:
        """List all uploaded videos, sorted by upload time (newest first)."""
        return sorted(
            self._videos.values(),
            key=lambda v: v.uploaded_at,
            reverse=True,
        )

    def delete_video(self, video_id: str) -> bool:
        """
        Delete video file and metadata.

        Args:
            video_id: Video ID to delete

        Returns:
            True if deleted successfully
        """
        video_info = self._videos.get(video_id)
        if not video_info:
            return False

        # Delete file
        try:
            file_path = Path(video_info.file_path)
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted video file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to delete video file: {e}")
            return False

        # Remove from memory
        del self._videos[video_id]

        # Update metadata file
        self._save_metadata()

        return True

    def get_video_path(self, video_id: str) -> Optional[Path]:
        """Get file system path for video."""
        video_info = self._videos.get(video_id)
        if video_info:
            path = Path(video_info.file_path)
            if path.exists():
                return path
        return None


# Global instance
video_manager = VideoManager()
