"""Tests for block_palette module."""

import numpy as np
import pytest

from mc_skin_statue.block_palette import BlockPalette


def test_palette_loads_all_categories():
    """Test loading all block categories."""
    palette = BlockPalette(categories=["all"], color_space="rgb")
    assert palette.get_block_count() > 50


def test_palette_loads_specific_category():
    """Test loading only wool category."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    assert palette.get_block_count() == 16


def test_find_nearest_basic():
    """Test basic color matching."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    # Pure red should map to red_wool
    red = np.array([[255, 0, 0]], dtype=np.uint8)
    indices, dist = palette.find_nearest(red)
    assert palette.get_block_id(int(indices[0])) == "red_wool"


def test_find_nearest_white():
    """Test white maps to white_wool."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    white = np.array([[255, 255, 255]], dtype=np.uint8)
    indices, dist = palette.find_nearest(white)
    assert palette.get_block_id(int(indices[0])) == "white_wool"


def test_find_nearest_black():
    """Test black maps to black_wool."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    black = np.array([[0, 0, 0]], dtype=np.uint8)
    indices, dist = palette.find_nearest(black)
    assert palette.get_block_id(int(indices[0])) == "black_wool"


def test_batch_mapping():
    """Test mapping multiple colors at once."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    colors = np.array([
        [255, 0, 0],
        [0, 255, 0],
        [0, 0, 255],
    ], dtype=np.uint8)
    indices, dist = palette.find_nearest(colors)
    assert len(indices) == 3


def test_block_state_format():
    """Test block state string format."""
    palette = BlockPalette(categories=["wool"], color_space="rgb")
    assert palette.get_block_state(0) == "minecraft:white_wool"
    assert palette.get_block_state(15) == "minecraft:pink_wool"
