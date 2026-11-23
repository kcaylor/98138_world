"""netCDF-4/HDF5 reader (feature 013: FR-001, FR-002; research R1, R3).

Files are written with h5py (tools/fixtures004/nc4.py). Not affiliated with or endorsed by The LEGO
Group.
"""

from pathlib import Path

import numpy as np
import pytest

from fixtures004.nc4 import write_netcdf4
from lego_image_processor.datasets.netcdf4 import (join_points, polar_stereographic_latlon,
                                                   read_netcdf4, read_netcdf4_files)
from lego_image_processor.datasets.readers import read_netcdf3

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "datasets"

NSIDC_NORTH = {"grid_mapping_name": "polar_stereographic", "straight_vertical_longitude_from_pole": -45.0,
               "false_easting": 0.0, "false_northing": 0.0, "latitude_of_projection_origin": 90.0,
               "standard_parallel": 70.0, "semi_major_axis": 6378273.0,
               "inverse_flattening": 298.27941112}
NSIDC_SOUTH = dict(NSIDC_NORTH, straight_vertical_longitude_from_pole=0.0,
                   latitude_of_projection_origin=-90.0, standard_parallel=-70.0)

# (x, y) -> (lat, lon) from NSIDC's G02202-ancillary-ps{n,s}25-v06r00.nc (2025-10-09).
REFERENCE = [
    (NSIDC_NORTH, -3837500.0, 5837500.0, 31.102671752463447, 168.32042246413275),
    (NSIDC_NORTH, -1337500.0, 3337500.0, 57.66145379040481, 156.83839836404925),
    (NSIDC_NORTH, 2412500.0, 837500.0, 66.7382184745462, 64.14445781119667),
    (NSIDC_NORTH, 3737500.0, -5337500.0, 34.472082798940995, -9.998975278568267),
    (NSIDC_SOUTH, -3937500.0, 4337500.0, -39.36486911321109, -42.23256960773262),
    (NSIDC_SOUTH, -1437500.0, 1837500.0, -68.70276513338207, -38.03653147351195),
    (NSIDC_SOUTH, 2312500.0, -662500.0, -68.0557679172009, 105.9862922390976),
    (NSIDC_SOUTH, 3937500.0, -3937500.0, -41.58344924468547, 135.0),
]


def _regular(path, values, lat, lon, attrs=None, dims=("time", "lat", "lon"), extra_coords=None):
    coords = {"lat": np.asarray(lat, dtype=np.float32), "lon": np.asarray(lon, dtype=np.float32)}
    coords.update(extra_coords or {})
    return write_netcdf4(path, coords, {"v": (dims, values, attrs or {})})


LAT = np.array([45.0, 15.0, -15.0, -45.0])  # descending, as PSL writes
LON = np.array([45.0, 135.0, 225.0, 315.0])  # 0..360


class TestRegular:
    def test_decode_fill_missing_range_and_packing(self, tmp_path):
        raw = np.arange(16, dtype=np.int16).reshape(4, 4)
        raw[0, 0], raw[0, 1], raw[0, 2] = -999, 9999, 500
        p = _regular(tmp_path / "a.nc", raw, LAT, LON,
                     {"_FillValue": -999, "missing_value": 9999, "valid_range": np.array([0, 100], np.int16),
                      "scale_factor": np.float32(0.5), "add_offset": np.float32(1.0), "units": "mm/day"},
                     dims=("lat", "lon"))
        g = read_netcdf4(p, "v")
        assert g.units == "mm/day" and not g.points
        assert list(g.lat) == [-45.0, -15.0, 15.0, 45.0]          # ascending
        assert list(g.lon) == [-135.0, -45.0, 45.0, 135.0]        # -180..180
        top = g.values[-1]                                         # the northern row (source row 0)
        assert np.isnan(top[2]) and np.isnan(top[3])               # fill and missing (lon 45, 135)
        assert np.isnan(top[0])                                    # 500 is outside valid_range
        assert top[1] == pytest.approx(3 * 0.5 + 1.0)              # lon 315 -> -45: raw 3

    def test_default_fill_floor_and_float_missing(self, tmp_path):
        v = np.ones((1, 4, 4), np.float32)
        v[0, 1, 1] = -9.96921e36
        p = _regular(tmp_path / "b.nc", v, LAT, LON, {"missing_value": np.float32(-9.96921e36)},
                     extra_coords={"time": np.array([0.0])})
        g = read_netcdf4(p, "v")                                   # time=1 is dropped
        assert g.values.shape == (4, 4) and np.isnan(g.values).sum() == 1

    def test_annual_and_climatology_mean(self, tmp_path):
        v = np.stack([np.full((4, 4), m, np.float32) for m in range(12)])
        v[3, 0, 0] = np.nan
        p = _regular(tmp_path / "c.nc", v, LAT, LON, extra_coords={"time": np.arange(12.0)})
        a = read_netcdf4(p, "v", reduce="annual-mean")
        assert np.isnan(a.values).sum() == 1 and np.nanmax(a.values) == pytest.approx(5.5)
        c = read_netcdf4(p, "v", reduce="climatology-mean")
        assert c.steps == 12 and c.counts.max() == 12 and c.counts.min() == 11
        assert np.isfinite(c.values).all()
        with pytest.raises(ValueError, match="declare a reduce rule"):
            read_netcdf4(p, "v")
        p2 = _regular(tmp_path / "d.nc", v[:6], LAT, LON, extra_coords={"time": np.arange(6.0)})
        with pytest.raises(ValueError, match="needs 12 months, found 6"):
            read_netcdf4(p2, "v", reduce="annual-mean")

    def test_errors(self, tmp_path):
        p = _regular(tmp_path / "e.nc", np.ones((4, 4)), LAT, LON, dims=("lat", "lon"))
        with pytest.raises(ValueError, match="variable 'w' not found"):
            read_netcdf4(p, "w")
        with pytest.raises(ValueError, match="netCDF-3 classic file, not netCDF-4"):
            read_netcdf4(FIXTURES / "ersst_v5_199712_ssta.nc", "ssta")
        junk = tmp_path / "junk.nc"
        junk.write_bytes(b"not a file at all")
        with pytest.raises(ValueError, match="not a netCDF-4/HDF5 file"):
            read_netcdf4(junk, "v")
        nocoord = write_netcdf4(tmp_path / "n.nc", {"a": np.arange(4.0), "b": np.arange(4.0)},
                                {"v": (("a", "b"), np.ones((4, 4)), {})})
        with pytest.raises(ValueError, match="no latitude/longitude coordinates"):
            read_netcdf4(nocoord, "v")

    def test_netcdf3_reader_still_rejects_netcdf4(self, tmp_path):
        p = _regular(tmp_path / "f.nc", np.ones((4, 4)), LAT, LON, dims=("lat", "lon"))
        with pytest.raises(ValueError, match="netCDF-4/HDF5 signature"):
            read_netcdf3(p, "v")


@pytest.mark.parametrize("name", ["ersst_v5_199712_ssta.nc", "ersst_v5_198812_ssta.nc"])
def test_ersst_month_as_netcdf4_reads_like_netcdf3(tmp_path, name):
    """ERSST v5 per-month layout (time=1, lev=1, lat, lon; int16 packed, _FillValue) in netCDF-4
    reads the same as the netCDF-3 original (owner decision 1: later El Niño update)."""
    from scipy.io import netcdf_file

    src = FIXTURES / name
    with netcdf_file(str(src), "r", mmap=False) as f:
        v = f.variables["ssta"]
        data = np.array(v[:])
        attrs = {k: (val.decode() if isinstance(val, bytes) else val) for k, val in v._attributes.items()}
        coords = {n: np.array(f.variables[n][:]) for n in ("time", "lev", "lat", "lon")}
    p = write_netcdf4(tmp_path / "ersst.nc", coords, {"ssta": (("time", "lev", "lat", "lon"), data, attrs)})
    a, b = read_netcdf4(p, "ssta"), read_netcdf3(src, "ssta")
    assert np.array_equal(a.lat, b.lat) and np.array_equal(a.lon, b.lon)
    assert np.allclose(a.values, b.values, equal_nan=True) and a.units == b.units


class TestPolarStereographic:
    @pytest.mark.parametrize("gm,x,y,lat,lon", REFERENCE)
    def test_matches_nsidc_ancillary(self, gm, x, y, lat, lon):
        la, lo = polar_stereographic_latlon(np.array([x]), np.array([y]), gm)
        assert la[0] == pytest.approx(lat, abs=1e-8)
        assert ((lo[0] - lon + 180) % 360 - 180) == pytest.approx(0, abs=1e-8)

    def test_pole_and_scale_factor_form(self):
        la, _ = polar_stereographic_latlon(np.array([0.0]), np.array([0.0]), NSIDC_NORTH)
        assert la[0] == pytest.approx(90.0)
        sphere = {"latitude_of_projection_origin": 90.0, "semi_major_axis": 6371000.0,
                  "scale_factor_at_projection_origin": 1.0, "straight_vertical_longitude_from_pole": 0.0}
        # sphere, k0 = 1: rho = 2 R tan(pi/4 - phi/2)
        rho = 2 * 6371000.0 * np.tan(np.pi / 4 - np.radians(60) / 2)
        la, lo = polar_stereographic_latlon(np.array([rho]), np.array([0.0]), sphere)
        assert la[0] == pytest.approx(60.0) and lo[0] == pytest.approx(90.0)

    def test_errors(self):
        with pytest.raises(ValueError, match="latitude_of_projection_origin"):
            polar_stereographic_latlon(np.zeros(1), np.zeros(1), dict(NSIDC_NORTH, latitude_of_projection_origin=45.0))
        with pytest.raises(ValueError, match="semi_major_axis"):
            polar_stereographic_latlon(np.zeros(1), np.zeros(1), {"latitude_of_projection_origin": 90.0})


class TestNsidcFixtures:
    def test_points_grid(self):
        g = read_netcdf4(FIXTURES / "nsidc_cdr_v6_n_199109_4x.nc", "cdr_seaice_conc_monthly")
        assert g.points and g.values.ndim == 1 and g.values.shape == g.lat.shape == g.lon.shape
        ok = np.isfinite(g.values)
        assert 0 <= np.nanmin(g.values) and np.nanmax(g.values) <= 1.0   # scale 0.01; flags dropped
        assert g.lat[ok].min() > 30 and g.lat.max() < 90 and (np.abs(g.lon) <= 180).all()

    def test_unsupported_grid_mapping(self, tmp_path):
        p = write_netcdf4(tmp_path / "lcc.nc", {"y": np.arange(3.0), "x": np.arange(3.0)},
                          {"v": (("y", "x"), np.ones((3, 3)), {"grid_mapping": "crs"})},
                          scalars={"crs": {"grid_mapping_name": "lambert_conformal_conic"}})
        with pytest.raises(ValueError, match="lambert_conformal_conic"):
            read_netcdf4(p, "v")

    def test_multi_file_climatology_mean(self):
        files = sorted(FIXTURES.glob("nsidc_cdr_v6_*_4x.nc"))
        assert len(files) == 4
        g = read_netcdf4_files(files, "cdr_seaice_conc_monthly", reduce="climatology-mean")
        n1 = read_netcdf4(files[0], "cdr_seaice_conc_monthly")
        n2 = read_netcdf4(files[1], "cdr_seaice_conc_monthly")
        s1 = read_netcdf4(files[2], "cdr_seaice_conc_monthly")
        assert g.points and g.steps == 4
        assert g.values.size == n1.values.size + s1.values.size          # two grids joined
        north = g.values[:n1.values.size]
        both = np.isfinite(n1.values) & np.isfinite(n2.values)
        assert np.allclose(north[both], (n1.values[both] + n2.values[both]) / 2)
        assert set(np.unique(g.counts[:n1.values.size])) <= {0, 1, 2}

    def test_single_file_and_errors(self):
        f = FIXTURES / "nsidc_cdr_v6_s_199102_4x.nc"
        a = read_netcdf4_files([f], "cdr_seaice_conc_monthly")
        assert a.points
        with pytest.raises(ValueError, match="no files"):
            read_netcdf4_files([], "x")


def test_join_points_mixes_regular_and_points():
    from lego_image_processor.datasets.grid import SourceGrid

    reg = SourceGrid(values=np.ones((2, 3)), lat=np.array([0.0, 1.0]), lon=np.array([0.0, 1.0, 2.0]))
    pts = SourceGrid(values=np.zeros(2), lat=np.array([5.0, 6.0]), lon=np.array([7.0, 8.0]), points=True)
    j = join_points([reg, pts])
    assert j.points and j.values.size == 8 and j.lat[-1] == 6.0
    with pytest.raises(ValueError, match="1-D values"):
        SourceGrid(values=np.zeros((2, 2)), lat=np.zeros(4), lon=np.zeros(4), points=True)
