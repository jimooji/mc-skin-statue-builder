"""Block color palette for mapping skin pixels to Minecraft blocks."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# Try to import Lab color space conversion (optional dependency)
try:
    from skimage.color import deltaE_ciede2000, rgb2lab

    LAB_AVAILABLE = True
except ImportError:
    LAB_AVAILABLE = False


# Color space conversion: RGB -> HSV

def rgb_to_hsv(rgb: np.ndarray) -> np.ndarray:
    """Convert RGB [0,255] to HSV [0,360] for H, [0,1] for S,V."""
    rgb = rgb.astype(np.float64) / 255.0
    maxc = rgb.max(axis=-1)
    minc = rgb.min(axis=-1)
    delta = maxc - minc

    h = np.zeros_like(maxc)
    s = np.zeros_like(maxc)
    v = maxc

    # Avoid division by zero
    nonzero = delta > 1e-8
    # Red is max
    r_max = (rgb[..., 0] == maxc) & nonzero
    h[r_max] = (60 * ((rgb[..., 1][r_max] - rgb[..., 2][r_max]) / delta[r_max]) + 360) % 360
    # Green is max
    g_max = (rgb[..., 1] == maxc) & nonzero
    h[g_max] = (60 * ((rgb[..., 2][g_max] - rgb[..., 0][g_max]) / delta[g_max]) + 120) % 360
    # Blue is max
    b_max = (rgb[..., 2] == maxc) & nonzero
    h[b_max] = (60 * ((rgb[..., 0][b_max] - rgb[..., 1][b_max]) / delta[b_max]) + 240) % 360

    s[nonzero] = delta[nonzero] / maxc[nonzero]

    return np.stack([h, s, v], axis=-1)


def hsv_distance(hsv1: np.ndarray, hsv2: np.ndarray) -> np.ndarray:
    """Weighted HSV distance emphasizing hue, then saturation, then value."""
    dh = np.abs(hsv1[..., 0] - hsv2[..., 0])
    dh = np.minimum(dh, 360 - dh) / 180.0  # normalize to [0,1]
    ds = np.abs(hsv1[..., 1] - hsv2[..., 1])
    dv = np.abs(hsv1[..., 2] - hsv2[..., 2])
    return 3.0 * dh + 1.0 * ds + 1.0 * dv


class BlockPalette:
    """Maps RGB colors to Minecraft block IDs using nearest-neighbor search."""

    PALETTE_CATEGORIES = {
        "wool",
        "concrete",
        "terracotta",
        "natural",
        "metal",
        "special",
        "shulker",
        "glazed_terracotta",
        "concrete_powder",
    }

    def __init__(
        self,
        categories: Optional[List[str]] = None,
        color_space: str = "rgb",
    ):
        """Initialize block palette.

        Args:
            categories: List of category names to include. None = all.
            color_space: Color space for distance calculation: 'rgb', 'lab', 'hsv'.
        """
        self.color_space = color_space.lower()
        if self.color_space == "lab" and not LAB_AVAILABLE:
            raise ImportError(
                "Lab color space requires scikit-image. Install with: "
                "pip install mc-skin-statue-builder[lab]"
            )

        # Load block colors from bundled JSON
        data_path = Path(__file__).with_name("data") / "block_colors.json"
        with data_path.open("r", encoding="utf-8") as f:
            all_blocks = json.load(f)

        # Filter by category
        if categories is None:
            categories = list(self.PALETTE_CATEGORIES)

        self.blocks: Dict[str, Tuple[int, int, int]] = {}
        for cat in categories:
            cat_lower = cat.lower()
            if cat_lower in all_blocks:
                for block_id, rgb in all_blocks[cat_lower].items():
                    self.blocks[block_id] = tuple(rgb)
            elif cat_lower == "all":
                for cat_blocks in all_blocks.values():
                    self.blocks.update(
                        {bid: tuple(rgb) for bid, rgb in cat_blocks.items()}
                    )
                break

        self.block_ids = list(self.blocks.keys())
        self.block_colors = np.array([self.blocks[bid] for bid in self.block_ids], dtype=np.uint8)

        # Precompute color-space transformed palette
        if self.color_space == "lab":
            self._palette_transformed = rgb2lab(self.block_colors.reshape(1, -1, 3) / 255.0).reshape(
                -1, 3
            )
        elif self.color_space == "hsv":
            self._palette_transformed = rgb_to_hsv(self.block_colors)
        else:
            self._palette_transformed = self.block_colors.astype(np.float64)

    def find_nearest(self, pixel_colors: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Find nearest block for each pixel color.

        Args:
            pixel_colors: Nx3 array of RGB colors [0,255].

        Returns:
            Tuple of (block_indices, distances).
        """
        if pixel_colors.ndim == 1:
            pixel_colors = pixel_colors.reshape(1, -1)

        if self.color_space == "lab":
            pixels_lab = rgb2lab(pixel_colors.reshape(1, -1, 3) / 255.0).reshape(-1, 3)
            distances = deltaE_ciede2000(
                pixels_lab[:, None, :], self._palette_transformed[None, :, :]
            )
        elif self.color_space == "hsv":
            pixels_hsv = rgb_to_hsv(pixel_colors)
            distances = hsv_distance(
                pixels_hsv[:, None, :], self._palette_transformed[None, :, :]
            )
        else:
            # RGB Euclidean distance
            distances = np.linalg.norm(
                pixel_colors[:, None, :].astype(np.float64)
                - self._palette_transformed[None, :, :],
                axis=2,
            )

        nearest_indices = np.argmin(distances, axis=1)
        min_distances = distances[np.arange(len(pixel_colors)), nearest_indices]
        return nearest_indices, min_distances

    def get_block_id(self, index: int) -> str:
        """Get block ID string by palette index."""
        return self.block_ids[index]

    def get_block_state(self, index: int) -> str:
        """Get full block state string for palette entry."""
        return f"minecraft:{self.block_ids[index]}"

    def get_block_count(self) -> int:
        """Total number of blocks in palette."""
        return len(self.block_ids)

    def get_block_rgb(self, index: int) -> Tuple[int, int, int]:
        """Get RGB color of a block by index."""
        return self.block_colors[index].tolist()
