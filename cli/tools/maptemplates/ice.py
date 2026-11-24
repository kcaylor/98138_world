"""Ice regions of a map template (feature 016, FR-020b; research R18; contracts/template-file.md
"Ice file"; data-model.md Template ice regions .template_id, .template_layout_sha256, .land_ice,
.sea_ice, .cells).

``python -m maptemplates ice-mask ID [--check]`` applies the kit's rules (``maps/ice.py``, written
for the kit by ``python -m kit31203 ice-mask``) at the template's own stud locations:

- **land ice**: land studs whose stored location lies in one of ``LAND_ICE_REGIONS``: Antarctica
  (south of 60° S) and the Greenland box without Iceland (strict bounds, ``in_region``);
- **sea ice**: ocean studs whose 1991-2020 warmest-month mean SST is at or below
  ``SEA_ICE_RULE["max_value"]`` (-1.5 °C), or that have no ERSST value and a location poleward of
  ``SEA_ICE_RULE["unobserved_lat"]`` (60°). A stud's value is the plain mean of the ERSST v5 values
  binned into it by the template's forward projection, as maps reproject (``reproject_layer`` on
  the template's ``TemplateProjection``); a stud with none has no value.

The file ``data/templates/<id>-ice.json`` lists both as board indices (row x 128 + column) and
records the template's layout digest (``source.template_layout_sha256``), not the file's SHA-256:
the digest leaves out the confirmation, so the file made from the unconfirmed template stays valid
when the owner confirms it; ``--check`` tells when corrections change classes. Needs no pyproj
(the forward formula is numpy). Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from lego_image_processor.datasets.grid import SourceGrid
from lego_image_processor.maps.ice import (DISCLAIMER, FORMAT_VERSION, LAND_ICE_REGIONS, SEA_ICE_RULE,
                                           TEMPLATE_COORDINATES, TEMPLATE_ICE_SUFFIX, IceRegions, in_region)
from lego_image_processor.maps.reproject import reproject_layer

GENERATOR = "cli/tools/maptemplates ice-mask"
RULE_KEYS = ("variable", "reduce", "max_value", "unobserved_lat")
IGNORED = {("source", "generated_on")}


def _check_template(template) -> None:
    if template.is_kit:
        raise ValueError("the kit's ice regions are kit_31203_ice.json, made by: PYTHONPATH=tools "
                         "python -m kit31203 ice-mask")


def land_ice_mask(template) -> np.ndarray:
    """Land studs (height x width) whose location lies in one of ``LAND_ICE_REGIONS``."""
    _check_template(template)
    lat, lon = template.locations()
    land = np.asarray(template.land, dtype=bool)
    out = np.zeros_like(land)
    for r, c in zip(*np.nonzero(land)):
        out[r, c] = any(in_region(lat[r, c], lon[r, c], reg) for reg in LAND_ICE_REGIONS)
    return out


def sea_ice_mask(warmest: SourceGrid, template) -> np.ndarray:
    """Ocean studs that ``SEA_ICE_RULE`` calls sea ice, from the warmest-month field ``warmest``
    (stud mean of the source values binned by the template's forward projection)."""
    _check_template(template)
    ocean = np.asarray(template.ocean, dtype=bool)
    fld = reproject_layer(warmest, template.grid_projection, ocean, "ocean")
    lat, _ = template.locations()
    with np.errstate(invalid="ignore"):
        cold = ocean & ~fld.filled & (fld.values <= SEA_ICE_RULE["max_value"])
        unobserved = ocean & fld.filled & (np.abs(lat) >= SEA_ICE_RULE["unobserved_lat"])
    return cold | unobserved


def derive(template, warmest: SourceGrid) -> IceRegions:
    """Both regions of ``template`` (board coordinates)."""
    return IceRegions(land=land_ice_mask(template), sea=sea_ice_mask(warmest, template))


def read_warmest(entry, dataset_path=None, cache_dir=None) -> SourceGrid:
    """The verified ERSST v5 1991-2020 long-term monthly means as the warmest-month field (raises
    ``generate.DatasetUnavailable`` when the file is missing or its checksum differs)."""
    from lego_image_processor.datasets import resolve, verify
    from lego_image_processor.datasets.cache import DatasetError
    from lego_image_processor.datasets.readers import read_netcdf3

    from .generate import DatasetUnavailable

    try:
        if dataset_path:
            if not Path(dataset_path).is_file():
                raise DatasetUnavailable(f"dataset {entry.id}: file not found: {dataset_path}")
            verify(entry, dataset_path)
            path = dataset_path
        else:
            path = resolve(entry, cache_dir)
    except DatasetError as exc:
        raise DatasetUnavailable(f"dataset {entry.id}: {exc}") from exc
    return read_netcdf3(path, SEA_ICE_RULE["variable"], reduce=SEA_ICE_RULE["reduce"])


def source_block(template, entry, generated_on: str) -> Dict[str, Any]:
    """``source`` of the ice file: the rules, the ERSST dataset, the template's layout digest."""
    return {
        "title": f"Ice-covered studs of the {template.id} template (palette chooser, feature 016)",
        "generator": GENERATOR,
        "generated_on": generated_on,
        "template_layout_sha256": template.layout_sha256,
        "land_ice": {"rule": ("land studs whose location lies in a region (strict bounds, minus excluded "
                              "boxes); the kit's rule (maps/ice.py), the regions of the 013-rainfall design"),
                     "regions": [dict(r) for r in LAND_ICE_REGIONS],
                     "locations": f"templates/{template.id}.json (stud locations)"},
        "sea_ice": {"rule": ("ocean studs whose 1991-2020 warmest-month mean SST (stud mean of the ERSST v5 "
                             "values binned by the template's forward projection, as maps reproject) is at or "
                             "below max_value, or with no ERSST value and a location poleward of "
                             "unobserved_lat; the kit's rule (maps/ice.py)"),
                    **{k: SEA_ICE_RULE[k] for k in RULE_KEYS},
                    "dataset": {"id": entry.id, "version": entry.version, "url": entry.url,
                                "sha256": entry.sha256, "citation": entry.citation, "license": entry.license}},
        "disclaimer": DISCLAIMER,
    }


def _cells(mask: np.ndarray) -> List[int]:
    return [int(i) for i in np.flatnonzero(np.asarray(mask).ravel())]


def ice_document(template, ice: IceRegions, source: Dict[str, Any]) -> Dict[str, Any]:
    """The JSON document for ``data/templates/<id>-ice.json``."""
    return {"format_version": FORMAT_VERSION, "template_id": template.id,
            "grid": {"width": template.width, "height": template.height,
                     "coordinates": TEMPLATE_COORDINATES.format(width=template.width)},
            "source": source,
            "land_ice": {"count": int(np.asarray(ice.land).sum()), "cells": _cells(ice.land)},
            "sea_ice": {"count": int(np.asarray(ice.sea).sum()), "cells": _cells(ice.sea)}}


def ice_path(template) -> Path:
    """Where the ice file of ``template`` lives: beside its template file."""
    return Path(template.path).with_name(f"{template.id}{TEMPLATE_ICE_SUFFIX}")


def _short(v: Any) -> str:
    import json

    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 80 else s[:77] + "..."


def _diff(a: Any, b: Any, path: Tuple[str, ...], out: List[str]) -> None:
    name = ".".join(path)
    if path in IGNORED or a == b:
        return
    if path[-1:] == ("cells",) and isinstance(a, list) and isinstance(b, list):
        sa, sb = set(a), set(b)
        gone, new = sorted(sa - sb), sorted(sb - sa)
        out.append(f"{name}: {len(gone)} only in the committed file{_first(gone)}, {len(new)} only "
                   f"regenerated{_first(new)}")
        return
    if isinstance(a, dict) and isinstance(b, dict):
        for k in list(a) + [k for k in b if k not in a]:
            sub = f"{name}.{k}" if name else k
            if k not in a:
                out.append(f"{sub}: missing in the committed file")
            elif k not in b:
                out.append(f"{sub}: not regenerated")
            else:
                _diff(a[k], b[k], path + (k,), out)
        return
    out.append(f"{name}: committed {_short(a)}, regenerated {_short(b)}")


def _first(cells: List[int]) -> str:
    if not cells:
        return ""
    r, c = divmod(cells[0], 128)
    return f" (first: index {cells[0]}, row {r}, column {c})"


def differences(committed: Dict[str, Any], regenerated: Dict[str, Any]) -> List[str]:
    """What differs between the committed ice file and the regenerated document, every field but
    ``source.generated_on``."""
    out: List[str] = []
    _diff(committed, regenerated, (), out)
    return out


def generated_on(committed: Optional[Dict[str, Any]], doc: Dict[str, Any], today: str) -> str:
    """The committed date while nothing else changed (rewrites are idempotent), else ``today``."""
    if committed and committed.get("source", {}).get("generated_on") and not differences(committed, doc):
        return committed["source"]["generated_on"]
    return today
