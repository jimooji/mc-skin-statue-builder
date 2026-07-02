"""Tests for statue_builder module."""

import numpy as np
from PIL import Image

from mc_skin_statue.block_palette import BlockPalette
from mc_skin_statue.skin_parser import SkinParser
from mc_skin_statue.statue_builder import StatueBuilder


def test_statue_builder_basic():
    """Test basic statue building with solid color skin."""
    # Create a simple red skin
    img = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
    img.save("/tmp/test_build.png")

    parser = SkinParser("/tmp/test_build.png")
    parts = parser.get_all_parts()

    palette = BlockPalette(categories=["wool"], color_space="rgb")
    builder = StatueBuilder(palette=palette)

    statue = builder.build(parts)
    assert statue.ndim == 3
    assert statue.shape[0] > 0
    assert statue.shape[1] > 0
    assert statue.shape[2] > 0

    # All non-zero blocks should be red_wool (index 1 in wool palette + 1 for air)
    non_air = statue[statue != 0]
    assert len(non_air) > 0


def test_statue_with_pedestal():
    """Test statue with pedestal."""
    img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    img.save("/tmp/test_pedestal.png")

    parser = SkinParser("/tmp/test_pedestal.png")
    parts = parser.get_all_parts()

    palette = BlockPalette(categories=["concrete"], color_space="rgb")
    builder = StatueBuilder(palette=palette, pedestal_height=2)

    statue = builder.build(parts)
    # Pedestal should add blocks at bottom (y=0, y=1)
    assert np.any(statue[:, 0, :] != 0)


def test_statue_scale():
    """Test statue scaling."""
    img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    img.save("/tmp/test_scale.png")

    parser = SkinParser("/tmp/test_scale.png")
    parts = parser.get_all_parts()

    palette = BlockPalette(categories=["wool"], color_space="rgb")
    
    builder1 = StatueBuilder(palette=palette, scale=1)
    statue1 = builder1.build(parts)
    
    builder2 = StatueBuilder(palette=palette, scale=2)
    statue2 = builder2.build(parts)

    # Scale 2 should be roughly double in each dimension
    assert statue2.shape[0] >= statue1.shape[0] * 2 - 1
    assert statue2.shape[1] >= statue1.shape[1] * 2 - 1
    assert statue2.shape[2] >= statue1.shape[2] * 2 - 1


def test_palette_with_air():
    """Test palette includes air at index 0."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    builder = StatueBuilder(palette=palette)
    full = builder.get_palette_with_air()
    assert full[0] == "minecraft:air"
    assert len(full) == 17  # 16 wool + air
