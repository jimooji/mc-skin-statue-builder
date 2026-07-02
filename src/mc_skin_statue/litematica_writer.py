"""Litematica NBT writer - generates .litematic schematic files."""

from __future__ import annotations

import gzip
import time
from pathlib import Path
from typing import List, Optional

import numpy as np


try:
    import nbtlib
    from nbtlib import Compound, Int, Long, String, Byte, Float, List as NBTList, LongArray

    NBT_AVAILABLE = True
except ImportError:
    NBT_AVAILABLE = False


class LitematicaWriter:
    """Writes 3D block arrays to Litematica .litematic format files."""

    # Litematica version constants
    VERSION = 6
    MINECRAFT_DATA_VERSION = 3953  # 1.21.1

    def __init__(self, version: int = 6, mc_data_version: int = 3953):
        """Initialize Litematica writer.

        Args:
            version: Litematica format version (default 6).
            mc_data_version: Minecraft data version (default 3953 for 1.21.1).
        """
        if not NBT_AVAILABLE:
            raise ImportError(
                "nbtlib is required for Litematica output. Install with: pip install nbtlib"
            )
        self.version = version
        self.mc_data_version = mc_data_version

    def write(
        self,
        region_name: str,
        blocks: np.ndarray,
        palette: List[str],
        output_path: str | Path,
        metadata: Optional[dict] = None,
    ):
        """Write a 3D block array to a .litematic file.

        Args:
            region_name: Name of the region (e.g., "Main").
            blocks: 3D numpy array of palette indices, shape (W, H, D).
                    Index 0 = air, 1+ = palette[1:].
            palette: List of block state strings, e.g. ["minecraft:air", "minecraft:stone"].
            output_path: Output file path.
            metadata: Optional dict with keys: name, author, description.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        w, h, d = blocks.shape
        total_blocks = int(np.count_nonzero(blocks))

        # Build metadata
        meta = {
            "name": metadata.get("name", "SkinStatue") if metadata else "SkinStatue",
            "author": metadata.get("author", "mc-skin-statue-builder") if metadata else "mc-skin-statue-builder",
            "description": metadata.get("description", "Generated from Minecraft skin") if metadata else "Generated from Minecraft skin",
        }

        # Build region
        region = self._build_region(region_name, blocks, palette)

        # Build root NBT
        root = Compound({
            "Version": Int(self.version),
            "MinecraftDataVersion": Int(self.mc_data_version),
            "Metadata": Compound({
                "Name": String(meta["name"]),
                "Author": String(meta["author"]),
                "Description": String(meta["description"]),
                "TimeCreated": Long(int(time.time() * 1000)),
                "TimeModified": Long(int(time.time() * 1000)),
                "EnclosingSize": Compound({
                    "x": Int(w),
                    "y": Int(h),
                    "z": Int(d),
                }),
                "TotalBlocks": Int(total_blocks),
                "TotalVolume": Int(w * h * d),
            }),
            "Regions": Compound({
                region_name: region,
            }),
        })

        # Write gzipped NBT
        with gzip.open(output_path, "wb") as f:
            nbtlib.write(root, f)

    def _build_region(
        self, region_name: str, blocks: np.ndarray, palette: List[str]
    ) -> Compound:
        """Build a Litematica region compound."""
        w, h, d = blocks.shape

        # Build BlockStatePalette
        palette_entries = []
        for block_state in palette:
            # Parse block state string
            if "[" in block_state:
                name = block_state[: block_state.index("[")]
                props_str = block_state[block_state.index("[") + 1 : -1]
                props = {}
                for prop in props_str.split(","):
                    if "=" in prop:
                        k, v = prop.split("=", 1)
                        props[k.strip()] = String(v.strip())
                entry = Compound({"Name": String(name)})
                if props:
                    entry["Properties"] = Compound(props)
            else:
                entry = Compound({"Name": String(block_state)})
            palette_entries.append(entry)

        # Encode BlockStates as packed long array
        block_states_longs = self._encode_block_states(blocks, len(palette))

        region = Compound({
            "Position": Compound({
                "x": Int(0),
                "y": Int(0),
                "z": Int(0),
            }),
            "Size": Compound({
                "x": Int(w),
                "y": Int(h),
                "z": Int(d),
            }),
            "BlockStatePalette": NBTList[Compound](palette_entries),
            "BlockStates": LongArray(block_states_longs),
            "Entities": NBTList[Compound]([]),
            "TileEntities": NBTList[Compound]([]),
            "PendingBlockTicks": NBTList[Compound]([]),
            "PendingFluidTicks": NBTList[Compound]([]),
        })

        return region

    def _encode_block_states(self, blocks: np.ndarray, palette_size: int) -> List[int]:
        """Encode block indices into Litematica LongArray format.

        Litematica uses bit-packing:
        - bits = ceil(log2(palette_size))
        - Each long (64-bit) stores floor(64/bits) block indices
        - Little-endian per block
        """
        bits = max(1, (palette_size - 1).bit_length())
        blocks_per_long = 64 // bits
        mask = (1 << bits) - 1

        total_blocks = blocks.size
        total_longs = (total_blocks + blocks_per_long - 1) // blocks_per_long

        # Flatten blocks in ZYX order (Litematica uses X-fastest, then Z, then Y)
        # Actually, Litematica iterates: for y in 0..h-1:
        #                                   for z in 0..d-1:
        #                                     for x in 0..w-1:
        w, h, d = blocks.shape
        flat = blocks.transpose(1, 2, 0).flatten()  # Y, Z, X order

        longs = []
        for long_idx in range(total_longs):
            value = 0
            for bit_idx in range(blocks_per_long):
                block_idx = long_idx * blocks_per_long + bit_idx
                if block_idx < total_blocks:
                    block_val = int(flat[block_idx]) & mask
                    value |= block_val << (bit_idx * bits)
            # Convert to signed 64-bit
            if value >= 2**63:
                value -= 2**64
            longs.append(value)

        return longs
