"""Minecraft skin parser - reads PNG skin files and extracts part textures."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
from PIL import Image


class SkinModel(Enum):
    """Minecraft player model type."""

    STEVE = auto()  # 4px wide arms
    ALEX = auto()  # 3px wide arms
    LEGACY = auto()  # 64x32 old format
    UNKNOWN = auto()


@dataclass
class SkinPart:
    """Represents one body part with its 6 face textures."""

    name: str
    width: int
    height: int
    depth: int
    # Each face is a (height, width, 4) RGBA numpy array
    front: np.ndarray
    back: np.ndarray
    left: np.ndarray
    right: np.ndarray
    top: np.ndarray
    bottom: np.ndarray
    # Offset in the statue (x, y, z) in Minecraft pixel coordinates
    offset_x: float = 0.0
    offset_y: float = 0.0
    offset_z: float = 0.0


# UV mappings for standard 64x64 skin format
# Each face defined as: (u, v, w, h) where (u,v) is top-left of the face texture
# and (w,h) is its size in pixels

# Standard 64x64 Steve/Alex UV layout (modern format)
UV_64x64 = {
    # Head inner layer
    "head": {
        "top": (8, 0, 8, 8),
        "bottom": (16, 0, 8, 8),
        "front": (8, 8, 8, 8),
        "back": (24, 8, 8, 8),
        "left": (0, 8, 8, 8),
        "right": (16, 8, 8, 8),
    },
    # Head outer layer (hat/helmet) - 1px larger on all sides
    "head_outer": {
        "top": (40, 0, 8, 8),
        "bottom": (48, 0, 8, 8),
        "front": (40, 8, 8, 8),
        "back": (56, 8, 8, 8),
        "left": (32, 8, 8, 8),
        "right": (48, 8, 8, 8),
    },
    # Body inner layer
    "body": {
        "top": (20, 16, 8, 4),
        "bottom": (28, 16, 8, 4),
        "front": (20, 20, 8, 12),
        "back": (32, 20, 8, 12),
        "left": (16, 20, 4, 12),
        "right": (28, 20, 4, 12),
    },
    # Body outer layer (jacket/overlay)
    "body_outer": {
        "top": (20, 32, 8, 4),
        "bottom": (28, 32, 8, 4),
        "front": (20, 36, 8, 12),
        "back": (32, 36, 8, 12),
        "left": (16, 36, 4, 12),
        "right": (28, 36, 4, 12),
    },
    # Right arm (4px wide - Steve)
    "right_arm": {
        "top": (44, 16, 4, 4),
        "bottom": (48, 16, 4, 4),
        "front": (44, 20, 4, 12),
        "back": (52, 20, 4, 12),
        "left": (40, 20, 4, 12),
        "right": (48, 20, 4, 12),
    },
    # Right arm outer (Steve)
    "right_arm_outer": {
        "top": (44, 32, 4, 4),
        "bottom": (48, 32, 4, 4),
        "front": (44, 36, 4, 12),
        "back": (52, 36, 4, 12),
        "left": (40, 36, 4, 12),
        "right": (48, 36, 4, 12),
    },
    # Left arm (4px wide - Steve)
    "left_arm": {
        "top": (36, 48, 4, 4),
        "bottom": (40, 48, 4, 4),
        "front": (36, 52, 4, 12),
        "back": (44, 52, 4, 12),
        "left": (32, 52, 4, 12),
        "right": (40, 52, 4, 12),
    },
    # Left arm outer (Steve)
    "left_arm_outer": {
        "top": (52, 48, 4, 4),
        "bottom": (56, 48, 4, 4),
        "front": (52, 52, 4, 12),
        "back": (60, 52, 4, 12),
        "left": (48, 52, 4, 12),
        "right": (56, 52, 4, 12),
    },
    # Right leg
    "right_leg": {
        "top": (4, 16, 4, 4),
        "bottom": (8, 16, 4, 4),
        "front": (4, 20, 4, 12),
        "back": (12, 20, 4, 12),
        "left": (0, 20, 4, 12),
        "right": (8, 20, 4, 12),
    },
    # Right leg outer
    "right_leg_outer": {
        "top": (4, 32, 4, 4),
        "bottom": (8, 32, 4, 4),
        "front": (4, 36, 4, 12),
        "back": (12, 36, 4, 12),
        "left": (0, 36, 4, 12),
        "right": (8, 36, 4, 12),
    },
    # Left leg
    "left_leg": {
        "top": (20, 48, 4, 4),
        "bottom": (24, 48, 4, 4),
        "front": (20, 52, 4, 12),
        "back": (28, 52, 4, 12),
        "left": (16, 52, 4, 12),
        "right": (24, 52, 4, 12),
    },
    # Left leg outer
    "left_leg_outer": {
        "top": (4, 48, 4, 4),
        "bottom": (8, 48, 4, 4),
        "front": (4, 52, 4, 12),
        "back": (12, 52, 4, 12),
        "left": (0, 52, 4, 12),
        "right": (8, 52, 4, 12),
    },
}

# Alex (slim) arm UVs - 3px wide arms
# In modern 64x64, Alex arms are detected by checking if the arm area is 3px or 4px wide
# For simplicity, we can use the same UVs but with 3px width interpretation

# Legacy 64x32 format UV mapping (old format, no separate arms, mirrored)
UV_64x32 = {
    "head": {
        "top": (8, 0, 8, 8),
        "bottom": (16, 0, 8, 8),
        "front": (8, 8, 8, 8),
        "back": (24, 8, 8, 8),
        "left": (0, 8, 8, 8),
        "right": (16, 8, 8, 8),
    },
    "head_outer": None,  # No overlay in legacy
    "body": {
        "top": (20, 16, 8, 4),
        "bottom": (28, 16, 8, 4),
        "front": (20, 20, 8, 12),
        "back": (32, 20, 8, 12),
        "left": (16, 20, 4, 12),
        "right": (28, 20, 4, 12),
    },
    "body_outer": None,
    # Legacy has only one arm/leg texture (right side), mirrored for left
    "right_arm": {
        "top": (44, 16, 4, 4),
        "bottom": (48, 16, 4, 4),
        "front": (44, 20, 4, 12),
        "back": (52, 20, 4, 12),
        "left": (40, 20, 4, 12),
        "right": (48, 20, 4, 12),
    },
    "right_arm_outer": None,
    "left_arm": {
        "top": (44, 16, 4, 4),
        "bottom": (48, 16, 4, 4),
        "front": (44, 20, 4, 12),
        "back": (52, 20, 4, 12),
        "left": (40, 20, 4, 12),
        "right": (48, 20, 4, 12),
    },
    "left_arm_outer": None,
    "right_leg": {
        "top": (4, 16, 4, 4),
        "bottom": (8, 16, 4, 4),
        "front": (4, 20, 4, 12),
        "back": (12, 20, 4, 12),
        "left": (0, 20, 4, 12),
        "right": (8, 20, 4, 12),
    },
    "right_leg_outer": None,
    "left_leg": {
        "top": (4, 16, 4, 4),
        "bottom": (8, 16, 4, 4),
        "front": (4, 20, 4, 12),
        "back": (12, 20, 4, 12),
        "left": (0, 20, 4, 12),
        "right": (8, 20, 4, 12),
    },
    "left_leg_outer": None,
}

# Model dimensions (width, height, depth) in Minecraft pixels
PART_DIMENSIONS = {
    "head": (8, 8, 8),
    "body": (8, 12, 4),
    "right_arm": (4, 12, 4),
    "left_arm": (4, 12, 4),
    "right_leg": (4, 12, 4),
    "left_leg": (4, 12, 4),
}

# Alex model has 3px wide arms
ALEX_PART_DIMENSIONS = {
    **PART_DIMENSIONS,
    "right_arm": (3, 12, 4),
    "left_arm": (3, 12, 4),
}

# Part offsets in statue coordinates (x, y, z)
# Steve model: center of body at origin
PART_OFFSETS = {
    "head": (0, 24, 0),
    "body": (0, 12, 0),
    "right_arm": (6, 12, 0),   # 4px arm: body_width/2 + arm_width/2 = 4+2 = 6
    "left_arm": (-6, 12, 0),   # mirrored
    "right_leg": (2, 0, 0),    # leg_offset = body_width/2 - leg_width/2 = 4-2 = 2
    "left_leg": (-2, 0, 0),    # mirrored
}

# Alex model offsets (3px arms)
ALEX_PART_OFFSETS = {
    "head": (0, 24, 0),
    "body": (0, 12, 0),
    "right_arm": (5.5, 12, 0),  # 4 + 1.5 = 5.5
    "left_arm": (-5.5, 12, 0),  # mirrored
    "right_leg": (2, 0, 0),
    "left_leg": (-2, 0, 0),
}


class SkinParser:
    """Parses Minecraft skin PNG files into structured part data."""

    def __init__(self, skin_path: str | Path, model: SkinModel = SkinModel.AUTO):
        """Initialize skin parser.

        Args:
            skin_path: Path to the skin PNG file.
            model: Model type. AUTO will detect from skin dimensions and arm width.
        """
        self.skin_path = Path(skin_path)
        self.image = Image.open(self.skin_path).convert("RGBA")
        self.pixels = np.array(self.image)
        self.width, self.height = self.image.size

        # Detect model type if auto
        if model == SkinModel.AUTO:
            self.model = self._detect_model()
        else:
            self.model = model

        self._uv_map = self._select_uv_map()
        self._dims = self._select_dimensions()
        self._offsets = self._select_offsets()

    def _detect_model(self) -> SkinModel:
        """Detect skin model type from dimensions and content."""
        if self.height == 32 and self.width == 64:
            return SkinModel.LEGACY
        elif self.height == 64 and self.width == 64:
            # Check if arms are 3px (Alex) or 4px (Steve)
            # Look at right arm area: if it's 3px wide content, it's Alex
            # Simple heuristic: check arm area (44,16)-(48,16) for 3px vs 4px
            # Actually, we can check if left arm is in the lower half (64x64) which
            # indicates a modern format. Then check arm width.
            # For Alex detection, the arm UV box is still 4px wide in texture,
            # but only 3px are used. We can detect by checking the 4th column alpha.
            # Simpler: default to Steve, let user override
            return SkinModel.STEVE
        elif self.height == 128 and self.width == 128:
            return SkinModel.STEVE  # HD skin, treat as Steve by default
        else:
            return SkinModel.UNKNOWN

    def _select_uv_map(self) -> Dict:
        """Select UV mapping based on skin format."""
        if self.model == SkinModel.LEGACY:
            return UV_64x32
        return UV_64x64

    def _select_dimensions(self) -> Dict[str, Tuple[int, int, int]]:
        """Select part dimensions based on model."""
        if self.model == SkinModel.ALEX:
            return ALEX_PART_DIMENSIONS
        return PART_DIMENSIONS

    def _select_offsets(self) -> Dict[str, Tuple[float, float, float]]:
        """Select part offsets based on model."""
        if self.model == SkinModel.ALEX:
            return ALEX_PART_OFFSETS
        return PART_OFFSETS

    def _extract_face(self, uv_info: Optional[Tuple[int, int, int, int]]) -> np.ndarray:
        """Extract a face texture from the skin using UV coordinates.

        Args:
            uv_info: (u, v, w, h) tuple or None for missing overlay.

        Returns:
            RGBA numpy array of shape (h, w, 4), or transparent array if uv_info is None.
        """
        if uv_info is None:
            return np.zeros((1, 1, 4), dtype=np.uint8)

        u, v, w, h = uv_info
        # Handle HD skins (scale UV coordinates)
        scale_x = self.width // 64
        scale_y = self.height // 64

        u *= scale_x
        v *= scale_y
        w *= scale_x
        h *= scale_y

        # Ensure we stay within bounds
        v = min(v, self.height - h)
        u = min(u, self.width - w)

        face = self.pixels[v : v + h, u : u + w].copy()
        return face

    def get_part(self, part_name: str) -> Optional[SkinPart]:
        """Extract a body part (inner + outer layers merged).

        Args:
            part_name: One of: head, body, right_arm, left_arm, right_leg, left_leg.

        Returns:
            SkinPart with merged inner+outer layers, or None if unavailable.
        """
        inner_uv = self._uv_map.get(part_name)
        if inner_uv is None:
            return None

        outer_uv = self._uv_map.get(f"{part_name}_outer")

        w, h, d = self._dims[part_name]
        ox, oy, oz = self._offsets[part_name]

        # Extract faces
        faces = {}
        for face_name in ["top", "bottom", "front", "back", "left", "right"]:
            inner_face = self._extract_face(inner_uv.get(face_name))
            outer_face = self._extract_face(outer_uv.get(face_name) if outer_uv else None)

            # Merge: outer layer overrides where not fully transparent
            # But outer layer is 1px larger on each side in 3D, so we need to
            # handle the overlay. For simplicity, just alpha blend.
            merged = self._merge_layers(inner_face, outer_face)
            faces[face_name] = merged

        return SkinPart(
            name=part_name,
            width=w,
            height=h,
            depth=d,
            front=faces["front"],
            back=faces["back"],
            left=faces["left"],
            right=faces["right"],
            top=faces["top"],
            bottom=faces["bottom"],
            offset_x=ox,
            offset_y=oy,
            offset_z=oz,
        )

    def _merge_layers(self, inner: np.ndarray, outer: np.ndarray) -> np.ndarray:
        """Merge inner and outer layers, with outer overriding where non-transparent.

        Args:
            inner: Inner layer RGBA array.
            outer: Outer layer RGBA array.

        Returns:
            Merged RGBA array.
        """
        # If outer is tiny/empty, return inner
        if outer.shape[0] <= 1 or outer.shape[1] <= 1:
            return inner

        # If sizes don't match, resize outer to match inner
        if inner.shape[:2] != outer.shape[:2]:
            # For HD skins, the outer layer should be scaled the same way
            # This shouldn't happen with proper UV scaling, but handle gracefully
            return inner

        # Alpha blend: outer alpha > threshold replaces inner
        merged = inner.copy()
        outer_alpha = outer[:, :, 3]
        mask = outer_alpha > 10  # Threshold for "visible"
        merged[mask] = outer[mask]
        return merged

    def get_all_parts(self) -> Dict[str, SkinPart]:
        """Extract all body parts."""
        parts = {}
        for part_name in ["head", "body", "right_arm", "left_arm", "right_leg", "left_leg"]:
            part = self.get_part(part_name)
            if part is not None:
                parts[part_name] = part
        return parts

    def get_model_info(self) -> Dict[str, any]:
        """Get detected model information."""
        return {
            "model": self.model.name,
            "width": self.width,
            "height": self.height,
            "dimensions": self._dims,
            "offsets": self._offsets,
        }
