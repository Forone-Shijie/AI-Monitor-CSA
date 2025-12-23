"""
Visualization Utilities - Drawing and display functions for pose detection.

Provides HUD-style visualization for pose detection results.
"""

from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.analysis.brace_position_detector import BracePositionResult
from src.perception.pose_detector import (
    BodyPart,
    POSE_CONNECTIONS,
    PoseResult,
)


# HUD color scheme
class HUDColors:
    """HUD-style color definitions (BGR format for OpenCV)."""

    BACKGROUND = (40, 22, 10)  # Dark blue
    PRIMARY = (255, 212, 0)  # Cyan
    SUCCESS = (0, 255, 0)  # Green
    WARNING = (0, 165, 255)  # Orange
    ERROR = (0, 0, 255)  # Red
    TEXT = (255, 255, 255)  # White
    TEXT_SECONDARY = (180, 180, 180)  # Light gray
    SKELETON = (255, 212, 0)  # Cyan for skeleton
    LANDMARK = (0, 255, 0)  # Green for landmarks
    GLOW = (255, 200, 100)  # Light cyan for glow effect


def draw_skeleton(
    frame: np.ndarray,
    pose_result: PoseResult,
    color: Tuple[int, int, int] = HUDColors.SKELETON,
    thickness: int = 2,
    landmark_radius: int = 4,
    min_visibility: float = 0.5,
) -> np.ndarray:
    """
    Draw skeleton on frame.

    Args:
        frame: BGR image to draw on
        pose_result: PoseResult from detector
        color: Line color (BGR)
        thickness: Line thickness
        landmark_radius: Radius for landmark circles
        min_visibility: Minimum visibility to draw

    Returns:
        Frame with skeleton drawn
    """
    if not pose_result.detected or not pose_result.landmarks:
        return frame

    output = frame.copy()
    h, w = output.shape[:2]

    # Draw connections first
    for start_part, end_part in POSE_CONNECTIONS:
        start_lm = pose_result.get_landmark(start_part)
        end_lm = pose_result.get_landmark(end_part)

        if start_lm and end_lm:
            if start_lm.visibility > min_visibility and end_lm.visibility > min_visibility:
                start_pt = start_lm.to_pixel(w, h)
                end_pt = end_lm.to_pixel(w, h)
                cv2.line(output, start_pt, end_pt, color, thickness)

    # Draw landmarks
    for lm in pose_result.landmarks:
        if lm.visibility > min_visibility:
            pt = lm.to_pixel(w, h)
            cv2.circle(output, pt, landmark_radius, HUDColors.LANDMARK, -1)
            cv2.circle(output, pt, landmark_radius + 2, color, 1)

    return output


def draw_angles(
    frame: np.ndarray,
    pose_result: PoseResult,
    show_angles: Optional[List[str]] = None,
    font_scale: float = 0.5,
    color: Tuple[int, int, int] = HUDColors.TEXT,
) -> np.ndarray:
    """
    Draw joint angle values on frame.

    Args:
        frame: BGR image to draw on
        pose_result: PoseResult from detector
        show_angles: List of angle names to show (None = all)
        font_scale: Font scale
        color: Text color (BGR)

    Returns:
        Frame with angles drawn
    """
    if not pose_result.detected or pose_result.angles is None:
        return frame

    output = frame.copy()
    h, w = output.shape[:2]

    # Define angle positions (body part to display near)
    angle_positions = {
        "left_elbow": BodyPart.LEFT_ELBOW,
        "right_elbow": BodyPart.RIGHT_ELBOW,
        "left_knee": BodyPart.LEFT_KNEE,
        "right_knee": BodyPart.RIGHT_KNEE,
        "left_shoulder": BodyPart.LEFT_SHOULDER,
        "right_shoulder": BodyPart.RIGHT_SHOULDER,
        "left_hip": BodyPart.LEFT_HIP,
        "right_hip": BodyPart.RIGHT_HIP,
    }

    angles_dict = pose_result.angles.to_dict()

    for angle_name, angle_value in angles_dict.items():
        if angle_value is None:
            continue

        if show_angles and angle_name not in show_angles:
            continue

        # Get position
        body_part = angle_positions.get(angle_name)
        if body_part:
            lm = pose_result.get_landmark(body_part)
            if lm and lm.visibility > 0.5:
                pt = lm.to_pixel(w, h)
                # Offset text slightly
                text_pt = (pt[0] + 10, pt[1] - 10)
                text = f"{angle_value:.0f}"
                cv2.putText(
                    output, text, text_pt,
                    cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1
                )

    # Draw torso and neck angles at center
    if pose_result.angles.torso is not None:
        left_shoulder = pose_result.get_landmark(BodyPart.LEFT_SHOULDER)
        right_shoulder = pose_result.get_landmark(BodyPart.RIGHT_SHOULDER)
        if left_shoulder and right_shoulder:
            mid_x = int((left_shoulder.x + right_shoulder.x) / 2 * w)
            mid_y = int((left_shoulder.y + right_shoulder.y) / 2 * h)
            text = f"Torso: {pose_result.angles.torso:.0f}"
            cv2.putText(
                output, text, (mid_x - 40, mid_y - 30),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 1
            )

    return output


def draw_brace_status(
    frame: np.ndarray,
    brace_result: BracePositionResult,
    position: Tuple[int, int] = (10, 30),
    font_scale: float = 0.6,
) -> np.ndarray:
    """
    Draw brace position status panel on frame.

    Args:
        frame: BGR image to draw on
        brace_result: BracePositionResult from detector
        position: Top-left position of panel
        font_scale: Font scale

    Returns:
        Frame with status panel drawn
    """
    output = frame.copy()
    x, y = position
    line_height = 25

    # Draw semi-transparent background
    panel_width = 280
    panel_height = 180
    overlay = output.copy()
    cv2.rectangle(
        overlay,
        (x - 5, y - 20),
        (x + panel_width, y + panel_height),
        HUDColors.BACKGROUND,
        -1
    )
    cv2.addWeighted(overlay, 0.7, output, 0.3, 0, output)

    # Draw border
    cv2.rectangle(
        output,
        (x - 5, y - 20),
        (x + panel_width, y + panel_height),
        HUDColors.PRIMARY,
        1
    )

    # Title
    title = "BRACE POSITION STATUS"
    cv2.putText(
        output, title, (x, y),
        cv2.FONT_HERSHEY_SIMPLEX, font_scale, HUDColors.PRIMARY, 1
    )
    y += line_height + 5

    # Body part statuses
    parts = [
        ("Torso", brace_result.torso),
        ("Head", brace_result.head),
        ("Arms", brace_result.arms),
        ("Legs", brace_result.legs),
    ]

    for part_name, status in parts:
        # Status indicator
        color = HUDColors.SUCCESS if status.is_compliant else HUDColors.ERROR
        indicator = "[OK]" if status.is_compliant else "[X]"

        text = f"{indicator} {status.part_name_cn}"
        cv2.putText(
            output, text, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, color, 1
        )

        # Value
        value_text = f"{status.current_value:.0f}"
        cv2.putText(
            output, value_text, (x + 180, y),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, HUDColors.TEXT_SECONDARY, 1
        )

        y += line_height

    y += 5

    # Overall status
    if brace_result.is_complete:
        status_text = "POSITION COMPLETE"
        status_color = HUDColors.SUCCESS
    else:
        pct = int(brace_result.compliance_ratio * 100)
        status_text = f"COMPLIANCE: {pct}%"
        status_color = HUDColors.WARNING

    cv2.putText(
        output, status_text, (x, y),
        cv2.FONT_HERSHEY_SIMPLEX, font_scale, status_color, 2
    )

    y += line_height

    # Hold duration
    if brace_result.hold_duration > 0:
        hold_text = f"HOLD: {brace_result.hold_duration:.1f}s"
        cv2.putText(
            output, hold_text, (x, y),
            cv2.FONT_HERSHEY_SIMPLEX, font_scale * 0.8, HUDColors.TEXT, 1
        )

    return output


def draw_hud_frame(
    frame: np.ndarray,
    title: str = "CC-SOP MONITOR",
    show_border: bool = True,
    show_corners: bool = True,
) -> np.ndarray:
    """
    Draw HUD-style frame overlay.

    Args:
        frame: BGR image to draw on
        title: Title text
        show_border: Whether to draw border
        show_corners: Whether to draw corner decorations

    Returns:
        Frame with HUD overlay
    """
    output = frame.copy()
    h, w = output.shape[:2]

    if show_border:
        # Draw border
        cv2.rectangle(output, (2, 2), (w - 3, h - 3), HUDColors.PRIMARY, 1)

    if show_corners:
        # Draw corner decorations
        corner_size = 30
        thickness = 2

        # Top-left
        cv2.line(output, (5, 5), (5 + corner_size, 5), HUDColors.PRIMARY, thickness)
        cv2.line(output, (5, 5), (5, 5 + corner_size), HUDColors.PRIMARY, thickness)

        # Top-right
        cv2.line(output, (w - 5, 5), (w - 5 - corner_size, 5), HUDColors.PRIMARY, thickness)
        cv2.line(output, (w - 5, 5), (w - 5, 5 + corner_size), HUDColors.PRIMARY, thickness)

        # Bottom-left
        cv2.line(output, (5, h - 5), (5 + corner_size, h - 5), HUDColors.PRIMARY, thickness)
        cv2.line(output, (5, h - 5), (5, h - 5 - corner_size), HUDColors.PRIMARY, thickness)

        # Bottom-right
        cv2.line(output, (w - 5, h - 5), (w - 5 - corner_size, h - 5), HUDColors.PRIMARY, thickness)
        cv2.line(output, (w - 5, h - 5), (w - 5, h - 5 - corner_size), HUDColors.PRIMARY, thickness)

    # Draw title
    cv2.putText(
        output, title, (15, 25),
        cv2.FONT_HERSHEY_SIMPLEX, 0.6, HUDColors.PRIMARY, 1
    )

    return output


def draw_pose_type(
    frame: np.ndarray,
    pose_result: PoseResult,
    position: Tuple[int, int] = (10, 60),
    font_scale: float = 0.7,
) -> np.ndarray:
    """
    Draw detected pose type on frame.

    Args:
        frame: BGR image to draw on
        pose_result: PoseResult from detector
        position: Text position
        font_scale: Font scale

    Returns:
        Frame with pose type drawn
    """
    if not pose_result.detected:
        return frame

    output = frame.copy()

    pose_names = {
        "unknown": "UNKNOWN",
        "standing": "STANDING",
        "sitting": "SITTING",
        "squatting": "SQUATTING",
        "bending": "BENDING",
        "brace_position": "BRACE",
    }

    pose_name = pose_names.get(pose_result.pose_type.value, "UNKNOWN")
    confidence_pct = int(pose_result.confidence * 100)

    text = f"POSE: {pose_name} ({confidence_pct}%)"
    cv2.putText(
        output, text, position,
        cv2.FONT_HERSHEY_SIMPLEX, font_scale, HUDColors.TEXT, 1
    )

    return output


def create_analysis_display(
    frame: np.ndarray,
    pose_result: PoseResult,
    brace_result: Optional[BracePositionResult] = None,
    show_skeleton: bool = True,
    show_angles: bool = True,
    show_pose_type: bool = True,
    show_brace_status: bool = True,
    show_hud_frame: bool = True,
) -> np.ndarray:
    """
    Create complete analysis display with all overlays.

    Args:
        frame: BGR image
        pose_result: PoseResult from detector
        brace_result: Optional BracePositionResult
        show_skeleton: Whether to draw skeleton
        show_angles: Whether to draw angles
        show_pose_type: Whether to draw pose type
        show_brace_status: Whether to draw brace status
        show_hud_frame: Whether to draw HUD frame

    Returns:
        Frame with all overlays
    """
    output = frame.copy()

    if show_skeleton:
        output = draw_skeleton(output, pose_result)

    if show_angles:
        output = draw_angles(output, pose_result)

    if show_pose_type:
        output = draw_pose_type(output, pose_result)

    if show_brace_status and brace_result:
        output = draw_brace_status(output, brace_result, position=(10, 90))

    if show_hud_frame:
        output = draw_hud_frame(output)

    return output
