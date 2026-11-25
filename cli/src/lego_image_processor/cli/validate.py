"""Validate CLI command for LEGO Image Processor."""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..palette.loader import LegoPalette
from ..layout.grid import DISCLAIMER, LayoutSchemaError, PositionPlacementGrid
from ..layout.kit_spec import load_kit_specification
from ..layout.validator import LayoutValidator


# Feature 017: a mask example's part type without a piece (an absent stud) or under the in-margin
# plaque; the other part types print as before.
_EXAMPLE_PART = {None: "no piece", "plaque_tile": "the plaque tile"}


def _example_part(part_type) -> str:
    return _EXAMPLE_PART.get(part_type, str(part_type))


@click.command()
@click.argument("layout_file", type=click.Path(exists=True))
@click.option(
    "--kit", "-k",
    default="31203",
    help="LEGO kit ID to validate against (default: 31203)"
)
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Output validation report file (JSON)"
)
def validate(layout_file: str, kit: str, output: str) -> None:
    """Validate layout against LEGO World Map kit inventory.

    Checks if a layout can be built with the parts of kit 31203: land uses the 1x1 round plate
    (6141) in White, ocean the 1x1 round tile (98138) in 9 colors, with quantities from the
    instructions' parts inventory (page 159). Layouts must use schema 2.0. A layout on a non-kit
    template (map build --template) is checked against that template's classes, and its margin's
    1x1 square tiles (3070b), which no kit has, are reported as beyond the kit. A layout with an
    in-margin plaque (map build --plaque) may lack exactly the studs under the plaque's tile, which
    is named in the summary and, like the square tiles, reported as beyond the kit (tile 6x6, part
    10202).
    Not affiliated with or endorsed by The LEGO Group.

    \b
    Examples:
        # Validate layout
        lego-image-processor validate layout.json

        # Validate and save report
        lego-image-processor validate layout.json -o report.json

        # Validate against specific kit
        lego-image-processor validate layout.json --kit 31203

    \b
    Output:
        - Buildability status (FULLY BUILDABLE / PARTIALLY BUILDABLE)
        - Buildability score (percentage of positions buildable)
        - Color availability violations (colors not in kit)
        - Quantity violations (colors exceeding kit inventory)
        - Suggested alternatives for unavailable colors (nearest kit color of
          the same part by CIEDE2000, shown as ΔE00)
    """
    try:
        # Load layout
        layout_path = Path(layout_file)
        click.echo(f"Loading layout: {layout_file}")

        if layout_path.suffix.lower() == ".json":
            with open(layout_path, "r", encoding="utf-8") as f:
                layout_data = f.read()
            layout = PositionPlacementGrid.from_json(layout_data)
        else:
            raise click.ClickException(
                f"Unsupported layout format: {layout_path.suffix}. Use JSON format."
            )

        plaque_rec = layout.plaque  # feature 017: the in-margin plaque; its studs carry no position
        total = len(layout.positions) if plaque_rec is not None else layout.total_positions
        click.echo(f"  Total positions: {total:,}")
        click.echo(f"  Land plates: {layout.land_positions:,}")
        click.echo(f"  Ocean tiles: {layout.ocean_positions:,}")
        template_rec = layout.template  # feature 016: None on the kit template
        if template_rec is not None:
            click.echo(f"  Margin square tiles: {layout.margin_positions:,}")
        if plaque_rec is not None:
            from ..maps.margin import plaque_text
            n = len(layout.plaque_positions)
            click.echo(f"  Plaque: {plaque_text(plaque_rec)} ({n:,} studs without a 1x1 piece)")
        click.echo(f"  Unique colors: {layout.unique_colors}")
        from ..layout.arrangement import arrangement_of
        click.echo(f"  Arrangement: {arrangement_of(layout).describe()}")
        if template_rec is not None:
            from ..templates import REHANG_RULE
            click.echo(f"  Template: {template_rec.get('id')} ({template_rec.get('title')}); arrangement A "
                       f"only ({REHANG_RULE})")
        click.echo()

        # Load kit specification
        click.echo(f"Loading kit specification: {kit} (LEGO World Map)")
        kit_spec = load_kit_specification(kit)
        click.echo(f"  Plate colors: {len(kit_spec.available_colors_plate)}")
        click.echo(f"  Tile colors: {len(kit_spec.available_colors_tile)}")
        click.echo(f"  Inventory: {kit_spec.inventory_lines} lines, "
                   f"cited from instructions page {kit_spec.inventory_page}")
        click.echo()

        # Load palette
        palette = LegoPalette.load_default()

        # Validate
        click.echo("Validating layout against kit...")
        validator = LayoutValidator(kit_spec=kit_spec, palette=palette)
        report = validator.validate(layout, layout_file=layout_file)

        # Summarize violations
        color_unavailable = [v for v in report.violations if v.type == "color_unavailable"]
        quantity_exceeded = [v for v in report.violations if v.type == "quantity_exceeded"]
        mask_mismatch = [v for v in report.violations if v.type == "mask_mismatch"]

        plate_unavailable = [v for v in color_unavailable if v.part_type == "plate"]
        tile_unavailable = [v for v in color_unavailable if v.part_type == "tile"]
        square_unavailable = [v for v in color_unavailable if v.part_type == "square_tile"]
        plaque_unavailable = [v for v in color_unavailable if v.part_type == "plaque_tile"]  # feature 017

        # Show plate (land) validation
        if layout.land_positions > 0:
            plate_color_count = layout.compute_statistics().color_frequency_by_part_type.get("plate", {})
            click.echo(f"  Checking plate colors ({len(plate_color_count)} colors)...")
            if plate_unavailable:
                click.echo(click.style(f"    ✗ {len(plate_unavailable)} plate colors unavailable in kit", fg="red"))
            else:
                click.echo(click.style("    ✓ All plate colors available in kit", fg="green"))

        # Show tile validation
        if layout.ocean_positions > 0:
            tile_color_count = layout.compute_statistics().color_frequency_by_part_type.get("tile", {})
            click.echo(f"  Checking tile colors ({len(tile_color_count)} colors)...")
            if tile_unavailable:
                click.echo(click.style(f"    ✗ {len(tile_unavailable)} tile colors unavailable in kit", fg="red"))
            else:
                click.echo(click.style("    ✓ All tile colors available in kit", fg="green"))

        # Square tiles of a non-kit template's margin (feature 016): never in the kit
        if square_unavailable:
            click.echo(f"  Checking square tile colors ({len(square_unavailable)} colors)...")
            click.echo(click.style(f"    ✗ {len(square_unavailable)} square tile colors unavailable in kit "
                                   "(no kit has part 3070b)", fg="red"))

        # The in-margin plaque's tile (feature 017, T082): never in the kit either
        if plaque_unavailable:
            from ..maps.margin import plaque_label
            click.echo("  Checking the plaque tile...")
            for v in plaque_unavailable:
                click.echo(click.style(f"    ✗ {plaque_label(v.part_id)} unavailable in kit "
                                       f"(no kit has part {v.part_id})", fg="red"))

        if report.template is None:
            # Land/sea mask under the layout's arrangement (feature 007)
            click.echo(f"  Checking land/sea mask (arrangement {report.arrangement})...")
            if mask_mismatch:
                click.echo(click.style(f"    ✗ {mask_mismatch[0].positions_required:,} positions do not match "
                                       f"the kit mask in arrangement {report.arrangement}", fg="red"))
            else:
                click.echo(click.style("    ✓ Plates on land and tiles on ocean", fg="green"))
        else:
            # The layout's own template (feature 016, FR-016)
            tid = report.template["id"]
            click.echo(f"  Checking template classes ({tid})...")
            if mask_mismatch:
                click.echo(click.style(f"    ✗ {mask_mismatch[0].positions_required:,} positions do not match "
                                       f"template {tid}", fg="red"))
            else:
                click.echo(click.style("    ✓ Plates on land, tiles on ocean and square tiles on the margin",
                                       fg="green"))

        # Show quantity validation
        click.echo("  Checking color quantities...")
        if quantity_exceeded:
            click.echo(click.style(f"    ✗ {len(quantity_exceeded)} colors exceed kit quantities", fg="red"))
        else:
            click.echo(click.style("    ✓ All color quantities within kit limits", fg="green"))

        click.echo()

        # Write report if requested
        if output:
            output_path = Path(output)
            output_path.write_text(report.to_json(), encoding="utf-8")

        # Show summary
        click.echo(click.style("Validation complete!", fg="green" if report.buildable else "yellow"))
        click.echo(f"  Buildability: {report.buildability_score * 100:.1f}% "
                  f"({'FULLY BUILDABLE' if report.buildable else 'PARTIALLY BUILDABLE'})")
        click.echo(f"  Violations: {len(report.violations)}")

        if output:
            click.echo(f"  Output: {output}")
        click.echo()

        # Show detailed violations if any
        if report.violations:
            click.echo(click.style("Violation details:", bold=True))

            for v in color_unavailable:
                click.echo(f"\n  Color Unavailable: {v.color_name} ({v.color_id})")
                click.echo(f"    Part type: {v.part_type} ({v.part_id})")
                if v.part_type == "plaque_tile":  # feature 017: positions are the studs it covers
                    from ..maps.margin import plaque_label
                    label = plaque_label(v.part_id).split(" (part ")[0]
                    click.echo(f"    Positions required: {v.positions_required} (studs under one {label})")
                else:
                    click.echo(f"    Positions required: {v.positions_required}")
                if v.suggested_alternative:
                    click.echo(f"    Suggested alternative: {v.suggested_alternative.color_name} "
                              f"(ΔE00 {v.suggested_alternative.color_distance:.1f})")

            for v in mask_mismatch:
                if v.template is None:
                    click.echo(f"\n  Mask Mismatch (arrangement {v.arrangement}): {v.positions_required:,} positions")
                else:
                    click.echo(f"\n  Mask Mismatch (template {v.template}): {v.positions_required:,} positions")
                expects = "kit mask" if v.template is None else f"template {v.template}"
                for e in v.examples[:3]:
                    click.echo(f"    ({e['x']}, {e['y']}): {_example_part(e['part_type'])}, {expects} expects "
                               f"{_example_part(e['expected'])}")

            for v in quantity_exceeded:
                click.echo(f"\n  Quantity Exceeded: {v.color_name} ({v.color_id})")
                click.echo(f"    Part type: {v.part_type} ({v.part_id})")
                click.echo(f"    Required: {v.positions_required}, Available: {v.kit_quantity}")
                click.echo(f"    Shortfall: {v.shortfall}")

            click.echo()

        # Final message
        if report.buildable:
            click.echo(click.style(
                "✓ This layout can be built with the standard LEGO World Map kit (31203)",
                fg="green"
            ))
        else:
            click.echo(click.style(
                "⚠ This layout requires additional parts beyond the standard kit.",
                fg="yellow"
            ))
            if output:
                click.echo(f"  See {output} for details and suggested alternatives.")
        click.echo(DISCLAIMER)

    except click.ClickException:
        raise
    except LayoutSchemaError as e:
        raise click.ClickException(str(e))
    except FileNotFoundError as e:
        raise click.ClickException(f"File not found: {e}")
    except json.JSONDecodeError as e:
        raise click.ClickException(f"Invalid JSON in layout file: {e}")
    except ValueError as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"Unexpected error: {e}")
