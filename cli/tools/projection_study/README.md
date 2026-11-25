# Projection study (maintainer research tool)

Rasterises world map projections onto rectangular boards of whole 16×16 modules and reports how
each fills the board. It produced the study (2026-11-22) behind constitution 3.0.0, Principle I
("Templates Fix the Canvas; the Kit Is the Reference"), and is the starting point for the
template-building tool of feature 016 (`specs/016-map-templates/`).

Not packaged; not part of the CLI. Outputs go to `<cache>/projection-study/` by default, outside
the repository.

## Running

The study needs [pyproj](https://pyproj4.github.io/pyproj/) (MIT), which is not a runtime
dependency. The maintainer group pins `pyproj >=3.7,<3.8` for the template tool
(`cli/tools/maptemplates`, feature 016; pyproj 3.8 needs Python 3.12): `poetry install --with
maintainer`. That pin runs every command here except `spilhaus-zoom` and the Spilhaus rows of
`survey` and `candidates`, which need PROJ ≥ 9.6, shipped in pyproj ≥ 3.8 wheels (Python ≥ 3.12).
From `cli/`, with the CLI's own dependencies installed:

    poetry install --with maintainer      # or, for Spilhaus on Python ≥ 3.12: pip install "pyproj>=3.8"
    PYTHONPATH=tools python -m projection_study calibrate     # kit grid vs the kit mask (94.2 %)
    PYTHONPATH=tools python -m projection_study survey        # 22 projections × 12 boards
    PYTHONPATH=tools python -m projection_study candidates    # 16 shortlisted boards, metrics + PNGs
    PYTHONPATH=tools python -m projection_study corners       # room for a corner plaque in the Winkel margin
    PYTHONPATH=tools python -m projection_study sheet         # outline-ring render, contact sheet
    PYTHONPATH=tools python -m projection_study spilhaus-zoom # land share as Spilhaus is cropped

All commands read ETOPO 2022 (10′), the pinned `etopo2022-surface-10m` dataset, from the verified
cache (`lego-image-processor dataset fetch etopo2022-surface-10m`) or `--dataset FILE`.

## Method

Each stud is supersampled 4×4 (2×2 in `survey`). Each subsample is inverse-projected to
(lat, lon) and kept only if a forward round trip returns to the same point. A stud is on the globe
when at least half its subsamples are, and land when at least half of those have elevation > 0.
The rest is margin (off the globe). The projection is scaled to fit the board ("contain") and
centred; the central meridian is the kit's, 11.1° E.

## Key results (16 candidates, 4×4 supersampling)

| Candidate | Board | On globe | Land / ocean / margin | Outline | Area p90/p10 |
|---|---|---|---|---|---|
| Kit grid (data-derived) | 8×5 | 100 % | 3184 / 7056 / 0 | — | 4.68 |
| Equal-area cylindrical φs 44.5° | 8×5 | 100 % | 3017 / 7223 / 0 | — | 1.00 |
| Mercator 80° N–64.6° S | 8×5 | 100 % | 3185 / 7055 / 0 | — | 14.25 |
| Winkel tripel (lat_1 50.4598°) | 8×5 | 81 % | 2554 / 5706 / 1980 | 286 | 1.90 |
| Equal Earth | 8×4 | 86 % | 2048 / 4974 / 1170 | 284 | 1.00 |
| Mollweide | 8×4 | 79 % | 1882 / 4574 / 1736 | 224 | 1.00 |
| Spilhaus | 6×6 | ~100 % | 4809 / 4401 / 6 | — | 232 |

The data-derived kit layout agrees with LEGO's mask on 94.2 % of studs (3,184 data land vs 3,062
kit land). On every shortlisted board each 16×16 module touches the globe, so shaped boards save
no bricks. In the Winkel tripel margin, each corner holds a 15 × 13-stud block clear of the
one-stud outline ring.

The committed `winkel-tripel` template (feature 016, made by `cli/tools/maptemplates`) fits the
projection's exact published extent, not the study's sampled one, so its numbers differ a little:
2,553 land, 5,691 ocean and 1,996 margin studs, outline ring 288, and a 14 × 14-stud block in each
corner (`lego-image-processor template show winkel-tripel`).

Not affiliated with or endorsed by The LEGO Group.
