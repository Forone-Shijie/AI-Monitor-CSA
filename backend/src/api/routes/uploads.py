"""
Upload Routes - API endpoints for video file upload and management.

Provides endpoints for:
- Uploading video files
- Listing uploaded videos
- Getting video information
- Streaming video playback
- Deleting videos
"""

import logging
from pathlib import Path
from typing import Generator

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse

from ..schemas import (
    ErrorResponse,
    VideoDeleteResponse,
    VideoInfoData,
    VideoListResponse,
    VideoUploadResponse,
)
from ...services.video_manager import video_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


def _video_info_to_data(video_info) -> VideoInfoData:
    """Convert VideoInfo to VideoInfoData schema."""
    return VideoInfoData(
        video_id=video_info.video_id,
        original_filename=video_info.original_filename,
        file_path=video_info.file_path,
        file_size=video_info.file_size,
        duration=video_info.duration,
        width=video_info.width,
        height=video_info.height,
        fps=video_info.fps,
        format=video_info.format,
        uploaded_at=video_info.uploaded_at,
    )


@router.post(
    "/videos",
    response_model=VideoUploadResponse,
    responses={400: {"model": ErrorResponse}, 413: {"model": ErrorResponse}},
)
async def upload_video(file: UploadFile = File(...)) -> VideoUploadResponse:
    """
    Upload a video file for analysis.

    - Max file size: 500MB
    - Allowed formats: mp4, avi, mkv, mov, webm

    Returns video metadata after processing.
    """
    # Validate filename
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Validate file
    error = video_manager.validate_file(file.filename, file_size)
    if error:
        raise HTTPException(status_code=400, detail=error)

    logger.info(f"Uploading video: {file.filename} ({file_size} bytes)")

    try:
        # Save video
        video_info = await video_manager.save_video(content, file.filename)

        return VideoUploadResponse(
            success=True,
            message="Video uploaded successfully",
            data=_video_info_to_data(video_info),
        )
    except Exception as e:
        logger.error(f"Failed to save video: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save video: {str(e)}")


@router.get("/videos", response_model=VideoListResponse)
async def list_videos() -> VideoListResponse:
    """List all uploaded videos."""
    videos = video_manager.list_videos()

    return VideoListResponse(
        success=True,
        message=f"Found {len(videos)} videos",
        data=[_video_info_to_data(v) for v in videos],
        total=len(videos),
    )


@router.get(
    "/videos/{video_id}",
    response_model=VideoUploadResponse,
    responses={404: {"model": ErrorResponse}},
)
async def get_video(video_id: str) -> VideoUploadResponse:
    """Get video information by ID."""
    video_info = video_manager.get_video(video_id)

    if not video_info:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    return VideoUploadResponse(
        success=True,
        message="Video found",
        data=_video_info_to_data(video_info),
    )


def _iter_file(file_path: Path, chunk_size: int = 1024 * 1024) -> Generator[bytes, None, None]:
    """Iterate over file in chunks."""
    with open(file_path, "rb") as f:
        while chunk := f.read(chunk_size):
            yield chunk


@router.get(
    "/videos/{video_id}/stream",
    responses={404: {"model": ErrorResponse}},
)
async def stream_video(video_id: str) -> StreamingResponse:
    """
    Stream video file for playback.

    Returns video file as a streaming response with proper content type.
    """
    video_info = video_manager.get_video(video_id)

    if not video_info:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    file_path = video_manager.get_video_path(video_id)
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Video file not found on disk")

    # Determine content type
    content_type_map = {
        "mp4": "video/mp4",
        "avi": "video/x-msvideo",
        "mkv": "video/x-matroska",
        "mov": "video/quicktime",
        "webm": "video/webm",
    }
    content_type = content_type_map.get(video_info.format, "video/mp4")

    return StreamingResponse(
        _iter_file(file_path),
        media_type=content_type,
        headers={
            "Content-Disposition": f'inline; filename="{video_info.original_filename}"',
            "Content-Length": str(video_info.file_size),
            "Accept-Ranges": "bytes",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Range",
        },
    )


@router.delete(
    "/videos/{video_id}",
    response_model=VideoDeleteResponse,
    responses={404: {"model": ErrorResponse}},
)
async def delete_video(video_id: str) -> VideoDeleteResponse:
    """Delete uploaded video."""
    video_info = video_manager.get_video(video_id)

    if not video_info:
        raise HTTPException(status_code=404, detail=f"Video not found: {video_id}")

    success = video_manager.delete_video(video_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete video")

    logger.info(f"Deleted video: {video_id}")

    return VideoDeleteResponse(
        success=True,
        message="Video deleted successfully",
        deleted_id=video_id,
    )
