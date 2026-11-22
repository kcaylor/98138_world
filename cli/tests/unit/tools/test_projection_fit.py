"""fit-projection recovers a known equirectangular frame from a synthetic world (T048)."""

import numpy as np

from kit31203 import projection_fit
from lego_image_processor.maps.build import land_mask_array


def _synthetic_world(lon0=-170.0, y0=40.0, s=26.0, step=0.5):
    kit = land_mask_array()
    lat = np.arange(-90 + step / 2, 90, step)
    lon = np.arange(-180 + step / 2, 180, step)
    row = np.floor(y0 - s * np.radians(lat)).astype(int)
    col = projection_fit.column_index(lon, lon0)
    z = np.full((len(lat), len(lon)), -100.0)
    ok = (row >= 0) & (row < 80)
    z[ok] = np.where(kit[row[ok]][:, col], 100.0, -100.0)
    return z, lat, lon, kit


def test_recovers_parameters():
    z, lat, lon, kit = _synthetic_world()
    r = projection_fit.fit(z, lat, lon, kit, lons=np.arange(-172.0, -168.0, 0.1),
                           y0_range=(38.0, 42.0), s_range=(24.0, 28.0))
    assert abs(r["left_edge_lon"] - -170.0) <= 0.3
    assert abs(r["equator_row"] - 40.0) <= 1.0
    assert abs(r["rows_per_radian"] - 26.0) <= 1.0
    land = (z > 0).astype(float)
    truth = projection_fit._agreement(projection_fit.land_by_column(land, lon, -170.0), np.radians(lat),
                                      kit, 40.0, 26.0)
    assert truth > 0.97
    assert r["agreement"]["equirectangular"] >= round(truth, 3) - 0.002
    assert r["agreement"]["equirectangular"] >= max(r["agreement"].values())
