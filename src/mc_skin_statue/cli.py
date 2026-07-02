"""Command-line interface for mc-skin-statue-builder."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import click
import numpy as np
from PIL import Image

from .block_palette import BlockPalette
from .litematica_writer import LitematicaWriter
from .skin_parser import SkinModel, SkinParser
from .statue_builder import StatueBuilder


@click.command()
@click.argument("skin_path", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "-o", "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    required=True,
    help="Output .litematic file path.",
)
@click.option(
    "--model",
    type=click.Choice(["steve", "alex", "auto", "legacy"], case_sensitive=False),
    default="auto",
    help="Player model type (default: auto-detect).",
)
@click.option(
    "--palette",
    type=str,
    default="all",
    help="Comma-separated block categories (wool,concrete,terracotta,natural,metal,special). "
         "Use 'all' for all categories.",
)
@click.option(
    "--color-space",
    type=click.Choice(["rgb", "lab", "hsv"], case_sensitive=False),
    default="rgb",
    help="Color space for matching (default: rgb).",
)
@click.option(
    "--fill-inner",
    type=str,
    default=None,
    help="Block ID to fill interior (default: hollow/air).",
)
@click.option(
    "--pedestal",
    type=int,
    default=0,
    help="Pedestal height in blocks (default: 0).",
)
@click.option(
    "--scale",
    type=int,
    default=1,
    help="Scale factor (default: 1).",
)
@click.option(
    "--preview",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Generate a 2D preview image of the statue.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["litematic"], case_sensitive=False),
    default="litematic",
    help="Output format (default: litematic).",
)
@click.option(
    "--name",
    type=str,
    default=None,
    help="Schematic name (default: output filename).",
)
@click.option(
    "--author",
    type=str,
    default="mc-skin-statue-builder",
    help="Schematic author.",
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Verbose output.",
)
def main(
    skin_path: Path,
    output: Path,
    model: str,
    palette: str,
    color_space: str,
    fill_inner: Optional[str],
    pedestal: int,
    scale: int,
    preview: Optional[Path],
    output_format: str,
    name: Optional[str],
    author: str,
    verbose: bool,
):
    """Convert a Minecraft skin PNG to a Litematica statue schematic.

    SKIN_PATH: Path to the skin PNG file (64x64, 64x32, or 128x128).
    """
    if verbose:
        click.echo(f"Loading skin: {skin_path}")

    # Parse skin
    model_enum = {
        "steve": SkinModel.STEVE,
        "alex": SkinModel.ALEX,
        "auto": SkinModel.AUTO,
        "legacy": SkinModel.LEGACY,
    }.get(model.lower(), SkinModel.AUTO)

    try:
        parser = SkinParser(skin_path, model=model_enum)
    except Exception as e:
        click.echo(f"Error parsing skin: {e}", err=True)
        sys.exit(1)

    model_info = parser.get_model_info()
    if verbose:
        click.echo(f"Detected model: {model_info['model']}")
        click.echo(f"Skin dimensions: {model_info['width']}x{model_info['height']}")

    # Extract parts
    parts = parser.get_all_parts()
    if not parts:
        click.echo("No valid parts found in skin.", err=True)
        sys.exit(1)

    if verbose:
        click.echo(f"Found parts: {', '.join(parts.keys())}")

    # Initialize palette
    categories = [c.strip() for c in palette.split(",")]
    try:
        block_palette = BlockPalette(categories=categories, color_space=color_space)
    except ImportError as e:
        click.echo(f"Color space error: {e}", err=True)
        sys.exit(1)

    if verbose:
        click.echo(f"Color space: {color_space}")
        click.echo(f"Palette size: {block_palette.get_block_count()} blocks")

    # Build statue
    builder = StatueBuilder(
        palette=block_palette,
        fill_inner=fill_inner,
        pedestal_height=pedestal,
        scale=scale,
    )

    if verbose:
        click.echo("Building 3D statue...")

    try:
        statue = builder.build(parts)
    except Exception as e:
        click.echo(f"Error building statue: {e}", err=True)
        sys.exit(1)

    w, h, d = statue.shape
    total_blocks = int(np.count_nonzero(statue))
    if verbose:
        click.echo(f"Statue dimensions: {w} x {h} x {d}")
        click.echo(f"Total blocks: {total_blocks}")

    # Generate full palette (with air at index 0)
    full_palette = builder.get_palette_with_air()

    # Write output
    if output_format == "litematic":
        if not output.suffix:
            output = output.with_suffix(".litematic")
        elif output.suffix.lower() != ".litematic":
            output = output.with_suffix(".litematic")

        metadata = {
            "name": name or output.stem,
            "author": author,
            "description": f"Generated from {skin_path.name}",
        }

        try:
            writer = LitematicaWriter()
            writer.write(
                region_name="Main",
                blocks=statue,
                palette=full_palette,
                output_path=output,
                metadata=metadata,
            )
        except Exception as e:
            click.echo(f"Error writing Litematica file: {e}", err=True)
            sys.exit(1)

    click.echo(f"Successfully saved statue to: {output}")

    # Generate preview if requested
    if preview:
        try:
            _generate_preview(statue, full_palette, block_palette, preview)
            click.echo(f"Preview saved to: {preview}")
        except Exception as e:
            click.echo(f"Error generating preview: {e}", err=True)


def _generate_preview(
    statue: np.ndarray,
    full_palette: list,
    block_palette: BlockPalette,
    output_path: Path,
):
    """Generate a 2D isometric-style preview of the statue."""
    w, h, d = statue.shape

    # Simple approach: render from front view (project onto X-Y plane)
    # Take the front-most non-air block for each (x, y) column
    preview = np.zeros((h, w, 3), dtype=np.uint8)

    for y in range(h):
        for x in range(w):
            for z in range(d):
                idx = statue[x, y, z]
                if idx > 0:
                    # Get block color from palette
                    block_id = full_palette[idx]
                    # Strip "minecraft:" prefix
                    short_id = block_id.replace("minecraft:", "")
                    if short_id in block_palette.blocks:
                        rgb = block_palette.blocks[short_id]
                        preview[h - 1 - y, x] = rgb
                    break

    img = Image.fromarray(preview)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(output_path)


if __name__ == "__main__":
    main()
