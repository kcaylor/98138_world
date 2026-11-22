"""Suitability metrics (FR-019; research R8; data-model.md SuitabilityReport)."""

import numpy as np

from lego_image_processor.maps.reproject import LayerField
from lego_image_processor.maps.suitability import THRESHOLDS, layer_report, min_neighbour_delta_e


def _field(variance_lost=0.1, filled=0):
    f = np.zeros((80, 128), bool)
    f.flat[:filled] = True
    return LayerField(values=np.zeros((80, 128)), samples=np.ones((80, 128), int), filled=f,
                      variance_lost=variance_lost)


def _classes(counts):
    c = np.full((80, 128), -1)
    flat = c.reshape(-1)
    i = 0
    for k, n in enumerate(counts):
        flat[i:i + n] = k
        i += n
    return c


KIT_TILES = ("lego_earth_blue", "lego_medium_azur", "lego_bright_bluish_green")


def _report(**kw):
    args = dict(cls="ocean", role="data", part_id="98138", colors=KIT_TILES,
                field=_field(), classes=_classes([100, 100, 100]), ordered=True, layer_cells=300)
    args.update(kw)
    return layer_report(**args)


def _codes(rep):
    return [w["code"] for w in rep["warnings"]]


def test_smooth_no_warnings():
    rep = _report()
    assert rep["warnings"] == []
    assert rep["variance_lost"] == 0.1
    assert rep["class_counts"] == [{"key": k, "cells": 100} for k in KIT_TILES]


def test_detail_loss_warning():
    rep = _report(field=_field(variance_lost=0.97))
    assert "detail_lost" in _codes(rep)
    assert "97" in next(w["message"] for w in rep["warnings"] if w["code"] == "detail_lost")


def test_filled_warning():
    rep = _report(field=_field(filled=40))
    assert rep["filled_share"] == round(40 / 300, 4)
    assert "filled" in _codes(rep)


def test_empty_class_warning():
    rep = _report(classes=_classes([150, 0, 150]))
    w = next(w for w in rep["warnings"] if w["code"] == "empty_class")
    assert "lego_medium_azur" in w["message"]


def test_close_colors_warning():
    # Bright Green and Dark Green? use two near-identical kit colors via a stub table
    pair, de = min_neighbour_delta_e(("lego_bright_green", "lego_bright_green_like"),
                                     rgb={"lego_bright_green": (75, 159, 74),
                                          "lego_bright_green_like": (77, 160, 75)})
    assert de < 5 and pair == ("lego_bright_green", "lego_bright_green_like")
    rep = _report(colors=("lego_a", "lego_b", "lego_c"),
                  rgb={"lego_a": (10, 10, 10), "lego_b": (11, 11, 11), "lego_c": (200, 200, 200)})
    w = next(w for w in rep["warnings"] if w["code"] == "colors_close")
    assert "lego_a" in w["message"] and "lego_b" in w["message"]


def test_supply_table():
    rep = _report(classes=_classes([500, 100, 100]))
    s = {r["key"]: r for r in rep["supply"]}
    assert s["lego_earth_blue"]["supplied"] == 393
    assert s["lego_earth_blue"]["within"] is False
    assert s["lego_medium_azur"]["within"] is True
    assert "over_supply" in _codes(rep)


def test_thresholds_recorded():
    assert THRESHOLDS == {"variance_lost": 0.5, "filled_share": 0.05, "min_delta_e00": 5.0}
    assert _report()["thresholds"] == THRESHOLDS
