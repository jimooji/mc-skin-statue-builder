"""Example: Programmatically build a statue from a skin file."""

from pathlib import Path

from mc_skin_statue.block_palette import BlockPalette
from mc_skin_statue.litematica_writer import LitematicaWriter
from mc_skin_statue.skin_parser import SkinParser
from mc_skin_statue.statue_builder import StatueBuilder


def build_statue_example(skin_path: str, output_path: str):
    """Build a statue from a skin and save as Litematica schematic.

    Args:
        skin_path: Path to the skin PNG file.
        output_path: Output .litematic file path.
    """
    # 1. Parse the skin
    print(f"Loading skin from {skin_path}...")
    parser = SkinParser(skin_path)
    model_info = parser.get_model_info()
    print(f"  Detected model: {model_info['model']}")
    print(f"  Skin size: {model_info['width']}x{model_info['height']}")

    # 2. Extract body parts
    parts = parser.get_all_parts()
    print(f"  Extracted parts: {', '.join(parts.keys())}")

    # 3. Create block palette (using wool + concrete for vibrant colors)
    print("Loading block palette...")
    palette = BlockPalette(
        categories=["wool", "concrete", "terracotta"],
        color_space="rgb",
    )
    print(f"  Using {palette.get_block_count()} block types")

    # 4. Build the statue
    print("Building 3D statue...")
    builder = StatueBuilder(
        palette=palette,
        fill_inner=None,  # Hollow interior (saves materials)
        pedestal_height=1,  # Add a 1-block stone pedestal
        scale=1,
    )
    statue = builder.build(parts)
    w, h, d = statue.shape
    print(f"  Statue size: {w}x{h}x{d} blocks")

    # 5. Write Litematica file
    print(f"Writing Litematica file to {output_path}...")
    full_palette = builder.get_palette_with_air()
    writer = LitematicaWriter()
    writer.write(
        region_name="Main",
        blocks=statue,
        palette=full_palette,
        output_path=output_path,
        metadata={
            "name": Path(skin_path).stem,
            "author": "mc-skin-statue-builder",
            "description": f"Generated from {Path(skin_path).name}",
        },
    )
    print("Done! Place the .litematic file in your .minecraft/schematics/ folder.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python build_statue.py <skin.png> <output.litematic>")
        sys.exit(1)

    build_statue_example(sys.argv[1], sys.argv[2])
