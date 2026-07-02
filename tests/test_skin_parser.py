"""Tests for skin_parser module."""

import numpy as np
import pytest
from PIL import Image

from mc_skin_statue.skin_parser import SkinModel, SkinParser, UV_64x64


def test_skin_parser_detects_64x64():
    """Test auto-detection of 64x64 skin format."""
    img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    img.save("/tmp/test_64x64.png")
    parser = SkinParser("/tmp/test_64x64.png")
    assert parser.model in (SkinModel.STEVE, SkinModel.AUTO)
    assert parser.width == 64
    assert parser.height == 64


def test_skin_parser_detects_legacy():
    """Test auto-detection of 64x32 legacy skin format."""
    img = Image.new("RGBA", (64, 32), (255, 255, 255, 255))
    img.save("/tmp/test_legacy.png")
    parser = SkinParser("/tmp/test_legacy.png")
    assert parser.model == SkinModel.LEGACY


def test_head_uv_extraction():
    """Test that head UV extraction returns correct dimensions."""
    img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    # Paint head front face red
    pixels = np.array(img)
    pixels[8:16, 8:16] = [255, 0, 0, 255]  # front face
    img = Image.fromarray(pixels)
    img.save("/tmp/test_head.png")

    parser = SkinParser("/tmp/test_head.png")
    head = parser.get_part("head")
    assert head is not None
    assert head.width == 8
    assert head.height == 8
    assert head.depth == 8
    assert head.front.shape == (8, 8, 4)
    # Front face should be red
    assert np.all(head.front[0, 0, :3] == [255, 0, 0])


def test_part_offsets():
    """Test that parts have correct offset positions."""
    img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    img.save("/tmp/test_offsets.png")
    parser = SkinParser("/tmp/test_offsets.png")
    head = parser.get_part("head")
    assert head.offset_y == 24


def test_all_parts_extracted():
    """Test that all 6 parts are extracted from a valid skin."""
    img = Image.new("RGBA", (64, 64), (255, 255, 255, 255))
    img.save("/tmp/test_parts.png")
    parser = SkinParser("/tmp/test_parts.png")
    parts = parser.get_all_parts()
    assert len(parts) == 6
    assert "head" in parts
    assert "body" in parts
    assert "right_arm" in parts
    assert "left_arm" in parts
    assert "right_leg" in parts
    assert "left_leg" in parts


def test_uv_mapping_complete():
    """Test that all UV mappings are complete for modern format."""
    for part_name, faces in UV_64x64.items():
        if faces is None:
            continue
        for face_name in ["top", "bottom", "front", "back", "left", "right"]:
            assert face_name in faces, f"Missing {face_name} for {part_name}"
            u, v, w, h = faces[face_name]
            assert u >= 0 and v >= 0
            assert w > 0 and h > 0
            assert u + w <= 64
            assert v + h <= 64
