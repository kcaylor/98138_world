"""`parts estimate` and `parts prices fetch` (feature 011).

`parts estimate` prices a layout from a BrickLink price guide snapshot, offline. Exit codes: 0 ok
(incomplete, stale or partial estimates are warnings); 1 input error (layout, snapshot, output
directory); 2 usage. `parts prices fetch` (maintainer, online) writes the snapshot; exit codes 0,
1 (input, missing credential variable, bad --lot, progress mismatch), 2, 5 (network, API, limits;
progress kept), 7 (credentials rejected), 130 (Ctrl-C; progress kept). Both are registered on the
existing `parts` group.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click

from ..kit.source import DISCLAIMER
from ..parts import LayoutInputError, read_layout
from ..prices.estimate import estimate_layout
from ..prices.snapshot import SnapshotError, load_snapshot
from ..prices.text import echo_estimate, estimate_summary_line
from ..prices.wording import DEFAULT_STALE_DAYS
from .map import CommandError
from .parts import parts


@parts.command("estimate")
@click.argument("layout_path", metavar="LAYOUT", type=click.Path(path_type=Path))
@click.option("--prices", "prices_path", type=click.Path(dir_okay=False, path_type=Path),
              help="Price snapshot (default: the packaged bricklink_price_guide.json)")
@click.option("--as-of", "as_of", type=click.DateTime(formats=["%Y-%m-%d"]), metavar="YYYY-MM-DD",
              help="Date staleness is judged against (default: today, UTC)")
@click.option("--stale-days", type=click.IntRange(min=1), default=DEFAULT_STALE_DAYS, show_default=True,
              help="Warn when the snapshot is older than this many days")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table",
              show_default=True)
@click.option("-o", "--output", type=click.Path(dir_okay=False, path_type=Path),
              help="Write the estimate as JSON (implies --format json)")
@click.option("--lines", "show_lines", is_flag=True,
              help="Also list every lot line of both estimates")
@click.option("-q", "--quiet", is_flag=True, help="No human output (errors still go to stderr)")
def estimate_cmd(layout_path, prices_path, as_of, stale_days, output_format, output, show_lines, quiet):
    """Estimate what a layout's map pieces cost: every piece, and on top of one 31203 kit.

    Offline: reads the layout and a price snapshot only; no network, no credentials.
    """
    try:
        layout = read_layout(layout_path)
    except LayoutInputError as exc:
        raise CommandError(str(exc), 1)
    try:
        snapshot = load_snapshot(prices_path)
    except SnapshotError as exc:
        raise CommandError(str(exc), 1)
    if output is not None and not output.parent.is_dir():
        raise CommandError(f"output directory {output.parent} does not exist", 1)
    day = as_of.date() if as_of is not None else datetime.now(timezone.utc).date()
    report = estimate_layout(layout, snapshot, as_of=day, stale_days=stale_days)
    if output is not None:
        output.write_text(report.to_json(), encoding="utf-8")
        if not quiet:
            click.echo(f"Wrote price estimate {output}: {estimate_summary_line(report)}")
            click.echo(DISCLAIMER)
        return
    if output_format == "json":
        click.echo(report.to_json(), nl=False)
        return
    if not quiet:
        echo_estimate(report, lines=show_lines)


# --- `parts prices fetch` (online, maintainer) ---------------------------------------------------

from typing import Optional  # noqa: E402

from ..prices.api_config import load_api_config  # noqa: E402
from ..prices.credentials import MissingCredentialsError, credentials_from_env  # noqa: E402
from ..prices.fetch import PriceFetchError, fetch_snapshot, make_lot_set  # noqa: E402
from ..prices.lots import all_cited_lots, named_lots, recipe_lots  # noqa: E402
from ..prices.text import UNCHECKED_NOTE, fetch_summary, resume_command, stop_message  # noqa: E402

DEFAULT_INTERVAL = 1.0
DEFAULT_MAX_ATTEMPTS = 5


@parts.group("prices")
def prices_group():
    """BrickLink price snapshots for `parts estimate` (maintainer)."""


def _previous_snapshot(compare: Optional[Path], output: Path):
    """The snapshot the change summary compares with (contracts/cli.md `--compare`)."""
    if compare is not None:
        try:
            return load_snapshot(compare)
        except SnapshotError as exc:
            raise CommandError(f"--compare: {exc}", 1)
    if output.is_file():
        try:
            return load_snapshot(output)
        except SnapshotError:
            pass
    try:
        return load_snapshot()
    except SnapshotError:
        return None


@prices_group.command("fetch")
@click.option("-o", "--output", required=True, type=click.Path(dir_okay=False, path_type=Path),
              help="Snapshot to write (from cli/: src/lego_image_processor/data/bricklink_price_guide.json)")
@click.option("--all-colors", is_flag=True,
              help="Every cited plate and tile color (84 lots) instead of the bundled recipes' lots")
@click.option("--lot", "lot_specs", multiple=True, metavar="PART:LEGO_COLOR_ID",
              help="Fetch only this lot (repeatable), for example 98138:140")
@click.option("--resume", is_flag=True, help="Continue a stopped fetch from <output stem>.progress.json")
@click.option("--write-partial", is_flag=True,
              help="On a stop, also write the snapshot (complete: false) from the lots fetched")
@click.option("--interval", type=click.FloatRange(min=0.5), default=DEFAULT_INTERVAL, show_default=True,
              help="Minimum seconds between request starts")
@click.option("--max-attempts", type=click.IntRange(1, 10), default=DEFAULT_MAX_ATTEMPTS,
              show_default=True, help="Attempts per request on 429, 5xx and network errors")
@click.option("--compare", type=click.Path(dir_okay=False, path_type=Path),
              help="Previous snapshot for the change summary (default: the existing output, else "
                   "the packaged snapshot)")
@click.option("-q", "--quiet", is_flag=True, help="Summary and errors only")
def fetch_cmd(output, all_colors, lot_specs, resume, write_partial, interval, max_attempts, compare,
              quiet):
    """Fetch BrickLink price-guide figures and write a dated, cited price snapshot.

    Uses the network. Credentials come only from BRICKLINK_CONSUMER_KEY, BRICKLINK_CONSUMER_SECRET,
    BRICKLINK_TOKEN_VALUE and BRICKLINK_TOKEN_SECRET; they are never printed or written.
    Exit codes: 0 ok; 1 input error; 2 usage; 5 network, API or limit stop (progress kept);
    7 credentials rejected.
    """
    if lot_specs and all_colors:
        raise click.UsageError("--lot and --all-colors cannot be used together")
    try:
        if lot_specs:
            kind, lots = "named", named_lots(lot_specs)
        elif all_colors:
            kind, lots = "all-cited", all_cited_lots()
        else:
            kind, lots = "recipes", recipe_lots()
    except ValueError as exc:
        raise CommandError(str(exc), 1)
    if not output.parent.is_dir():
        raise CommandError(f"output directory {output.parent} does not exist", 1)
    try:
        credentials = credentials_from_env()
    except MissingCredentialsError as exc:
        raise CommandError(str(exc), 1)
    try:
        api = load_api_config()
    except ValueError as exc:
        raise CommandError(str(exc), 1)
    previous = _previous_snapshot(compare, output)
    resume_cmd = resume_command(
        output, all_colors=all_colors, lots=lot_specs, write_partial=write_partial, compare=compare,
        interval=None if interval == DEFAULT_INTERVAL else interval,
        max_attempts=None if max_attempts == DEFAULT_MAX_ATTEMPTS else max_attempts)
    if not quiet and not api.checked:
        click.echo(UNCHECKED_NOTE)
    try:
        result = fetch_snapshot(lots, credentials, output=output, lot_set=make_lot_set(kind, lots),
                                resume=resume, write_partial=write_partial, interval=interval,
                                max_attempts=max_attempts, api=api,
                                echo=None if quiet else click.echo)
    except PriceFetchError as exc:
        raise CommandError(stop_message(exc, resume_cmd), exc.exit_code)
    for line in fetch_summary(output, result.snapshot, previous):
        click.echo(line)
