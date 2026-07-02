"""3D statue builder - converts skin parts into a voxel statue."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import numpy as np

from .block_palette import BlockPalette
from .skin_parser import SkinPart


class StatueBuilder:
    """Builds a 3D voxel statue from skin parts and block palette."""

    def __init__(
        self,
        palette: BlockPalette,
        fill_inner: Optional[str] = None,
        pedestal_height: int = 0,
        scale: int = 1,
    ):
        """Initialize statue builder.

        Args:
            palette: BlockPalette for color mapping.
            fill_inner: Block ID to fill interior (None = air/hollow).
            pedestal_height: Height of pedestal/base under the statue.
            scale: Integer scale factor (1 = 1:1 with Minecraft model).
        """
        self.palette = palette
        self.fill_inner = fill_inner
        self.pedestal_height = pedestal_height
        self.scale = max(1, int(scale))

    def build(self, parts: Dict[str, SkinPart]) -> np.ndarray:
        """Build a 3D statue from skin parts.

        Args:
            parts: Dictionary of SkinPart objects keyed by name.

        Returns:
            3D numpy array of block palette indices, shape (W, H, D).
            Index 0 is reserved for air (empty).
        """
        # Determine statue bounds
        min_x, max_x = float("inf"), float("-inf")
        min_y, max_y = float("inf"), float("-inf")
        min_z, max_z = float("inf"), float("-inf")

        for part in parts.values():
            half_w = part.width / 2
            half_d = part.depth / 2
            px = [part.offset_x - half_w, part.offset_x + half_w]
            py = [part.offset_y, part.offset_y + part.height]
            pz = [part.offset_z - half_d, part.offset_z + half_d]
            min_x, max_x = min(min_x, min(px)), max(max_x, max(px))
            min_y, max_y = min(min_y, min(py)), max(max_y, max(py))
            min_z, max_z = min(min_z, min(pz)), max(max_z, max(pz))

        # Add pedestal
        if self.pedestal_height > 0:
            min_y -= self.pedestal_height

        # Apply scale
        size_x = max(1, int(np.ceil((max_x - min_x) * self.scale)))
        size_y = max(1, int(np.ceil((max_y - min_y) * self.scale)))
        size_z = max(1, int(np.ceil((max_z - min_z) * self.scale)))

        # Initialize with air (index 0)
        statue = np.zeros((size_x, size_y, size_z), dtype=np.int32)

        # Build pedestal first
        if self.pedestal_height > 0:
            self._build_pedestal(statue, size_x, size_z)

        # Build each part
        for part_name, part in parts.items():
            self._build_part(statue, part, min_x, min_y, min_z)

        return statue

    def _build_pedestal(self, statue: np.ndarray, size_x: int, size_z: int):
        """Build a pedestal under the statue."""
        pedestal_block = "stone"
        for bid in self.palette.block_ids:
            if "stone" in bid:
                pedestal_block = bid
                break
            elif "concrete" in bid and "gray" in bid:
                pedestal_block = bid
                break

        try:
            pedestal_idx = self.palette.block_ids.index(pedestal_block) + 1
        except ValueError:
            pedestal_idx = 1 if self.palette.block_ids else 0

        for py in range(self.pedestal_height):
            for px in range(size_x):
                for pz in range(size_z):
                    center_x = size_x / 2 - 0.5
                    center_z = size_z / 2 - 0.5
                    dx = abs(px - center_x)
                    dz = abs(pz - center_z)
                    radius = min(size_x, size_z) / 2 - 0.5
                    if dx <= radius and dz <= radius:
                        statue[px, py, pz] = pedestal_idx

    def _build_part(
        self,
        statue: np.ndarray,
        part: SkinPart,
        min_x: float,
        min_y: float,
        min_z: float,
    ):
        """Build a single body part into the statue array."""
        w, h, d = part.width, part.height, part.depth
        ox, oy, oz = part.offset_x, part.offset_y, part.offset_z

        for vy in range(h):
            for vz in range(d):
                for vx in range(w):
                    block_idx = self._get_block_for_voxel(part, vx, vy, vz, w, h, d)
                    if block_idx is not None and block_idx > 0:
                        world_x = int((ox - w / 2 + vx - min_x) * self.scale)
                        world_y = int((oy + vy - min_y) * self.scale)
                        world_z = int((oz - d / 2 + vz - min_z) * self.scale)

                        for sx in range(self.scale):
                            for sy in range(self.scale):
                                for sz in range(self.scale):
                                    tx = world_x + sx
                                    ty = world_y + sy
                                    tz = world_z + sz
                                    if (
                                        0 <= tx < statue.shape[0]
                                        and 0 <= ty < statue.shape[1]
                                        and 0 <= tz < statue.shape[2]
                                    ):
                                        statue[tx, ty, tz] = block_idx

    def _get_block_for_voxel(
        self, part: SkinPart, vx: int, vy: int, vz: int, w: int, h: int, d: int
    ) -> Optional[int]:
        """Determine the block palette index for a voxel based on its face.

        Returns 0 for air/completely transparent, or None for interior (if hollow).
        """
        face_name = None
        tex_u = 0
        tex_v = 0

        if vz == d - 1:  # Front face (facing +Z)
            face_name = "front"
            tex_u = vx
            tex_v = h - 1 - vy  # Flip Y: texture top = model top
        elif vz == 0:  # Back face (facing -Z)
            face_name = "back"
            tex_u = w - 1 - vx  # Mirror horizontally
            tex_v = h - 1 - vy
        elif vx == 0:  # Left face (facing -X)
            face_name = "left"
            tex_u = d - 1 - vz
            tex_v = h - 1 - vy
        elif vx == w - 1:  # Right face (facing +X)
            face_name = "right"
            tex_u = vz
            tex_v = h - 1 - vy
        elif vy == h - 1:  # Top face (facing +Y)
            face_name = "top"
            tex_u = vx
            tex_v = d - 1 - vz
        elif vy == 0:  # Bottom face (facing -Y)
            face_name = "bottom"
            tex_u = vx
            tex_v = vz
        else:
            # Interior voxel
            if self.fill_inner is not None:
                try:
                    return self.palette.block_ids.index(self.fill_inner) + 1
                except ValueError:
                    return 1 if self.palette.block_ids else 0
            return None

        face_data = getattr(part, face_name)
        if face_data is None or face_data.size == 0:
            return None

        fh, fw = face_data.shape[:2]
        tex_u = max(0, min(tex_u, fw - 1))
        tex_v = max(0, min(tex_v, fh - 1))

        pixel = face_data[tex_v, tex_u]

        # Check alpha (transparent = air)
        if pixel[3] < 10:
            return 0

        # Map RGB to nearest block
        rgb = pixel[:3].reshape(1, 3)
        indices, _ = self.palette.find_nearest(rgb)
        return int(indices[0]) + 1  # +1 because palette index 0 is air

    def get_palette_with_air(self) -> List[str]:
        """Get full palette list including air at index 0."""
        return ["minecraft:air"] + [
            self.palette.get_block_state(i) for i in range(self.palette.get_block_count())
        ]

    def get_statue_dimensions(self, parts: Dict[str, SkinPart]) -> Tuple[int, int, int]:
        """Get statue dimensions without building it."""
        statue = self.build(parts)
        return statue.shape
