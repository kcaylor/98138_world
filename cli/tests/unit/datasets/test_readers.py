"""Readers for DODS, netCDF-3 and .npy grids (research R3-R5; data-model.md SourceGrid)."""

import numpy as np
import pytest
from scipy.io import netcdf_file

from lego_image_processor.datasets.readers import read_dods, read_netcdf3, read_npy, read_dataset
from lego_image_processor.datasets.registry import DatasetEntry


def write_dods(path, z, lat, lon, name="z"):
    """A DAP2 binary response: DDS text, 'Data:\\n', then XDR arrays (count twice, values)."""
    dds = (f"Dataset {{\n    Grid {{\n     ARRAY:\n        Float32 {name}[lat = {len(lat)}][lon = {len(lon)}];\n"
           f"     MAPS:\n        Float64 lat[lat = {len(lat)}];\n        Float64 lon[lon = {len(lon)}];\n"
           f"    }} {name};\n}} test;\n")
    out = bytearray(dds.encode("ascii") + b"\nData:\n")
    for arr, dt in ((np.asarray(z, ">f4").ravel(), ">f4"), (np.asarray(lat, ">f8"), ">f8"),
                    (np.asarray(lon, ">f8"), ">f8")):
        n = arr.size
        out += n.to_bytes(4, "big") + n.to_bytes(4, "big") + arr.astype(dt).tobytes()
    path.write_bytes(bytes(out))


def _entry(fmt, **kw):
    base = dict(id="t", version="1", kind="local", title="T", publisher="P", format=fmt,
                variables={"v": {"units": "m"}}, class_rule={}, license="PD", citation="C.")
    base.update(kw)
    return DatasetEntry(**base)


class TestDods:
    def test_round_trip(self, tmp_path):
        lat = np.array([-45.0, 45.0])
        lon = np.array([-90.0, 0.0, 90.0])
        z = np.array([[1, 2, 3], [4, 5, -99999]], dtype=float)
        p = tmp_path / "t.dods"
        write_dods(p, z, lat, lon)
        g = read_dods(p, "z", fill=-99999)
        assert g.values.shape == (2, 3)
        assert g.values[0].tolist() == [1, 2, 3]
        assert np.isnan(g.values[1, 2])
        assert g.lat.tolist() == [-45, 45] and g.lon.tolist() == [-90, 0, 90]

    def test_descending_lat_and_0_360_lon(self, tmp_path):
        lat = np.array([45.0, -45.0])
        lon = np.array([0.0, 90.0, 180.0, 270.0])
        z = np.array([[1, 2, 3, 4], [5, 6, 7, 8]], dtype=float)
        p = tmp_path / "t.dods"
        write_dods(p, z, lat, lon)
        g = read_dods(p, "z")
        assert g.lat.tolist() == [-45, 45]
        assert g.lon.tolist() == [-180, -90, 0, 90]
        # lon 180 -> -180 comes first; south row (5..8) first
        assert g.values.tolist() == [[7, 8, 5, 6], [3, 4, 1, 2]]

    def test_not_dods(self, tmp_path):
        p = tmp_path / "x.dods"
        p.write_bytes(b"<html>error</html>")
        with pytest.raises(ValueError, match="DODS"):
            read_dods(p, "z")


class TestNetcdf3:
    def _write(self, path, data, missing=-9.96921e36):
        f = netcdf_file(str(path), "w")
        f.createDimension("time", data.shape[0])
        f.createDimension("lat", data.shape[1])
        f.createDimension("lon", data.shape[2])
        lat = f.createVariable("lat", "f4", ("lat",))
        lat[:] = np.linspace(10, -10, data.shape[1])
        lon = f.createVariable("lon", "f4", ("lon",))
        lon[:] = np.linspace(0, 360, data.shape[2], endpoint=False)
        v = f.createVariable("sst", "f4", ("time", "lat", "lon"))
        v.missing_value = np.float32(missing)
        v.units = "degC"
        v[:] = data
        f.close()

    def test_annual_mean_only_where_all_months_valid(self, tmp_path):
        data = np.ones((12, 3, 4), dtype=np.float32) * np.arange(12, dtype=np.float32)[:, None, None]
        data[5, 0, 0] = -9.96921e36
        p = tmp_path / "s.nc"
        self._write(p, data)
        g = read_netcdf3(p, "sst", reduce="annual-mean")
        assert g.values.shape == (3, 4)
        assert g.lat.tolist() == [-10, 0, 10]
        # (lat 10, lon 0) had a missing month: lat reversed, so it is the last row
        assert np.isnan(g.values[2, 2])
        assert np.nanmax(np.abs(g.values - 5.5)) < 1e-5
        assert g.units == "degC"

    def test_single_time_without_reduce(self, tmp_path):
        p = tmp_path / "s.nc"
        self._write(p, np.full((1, 3, 4), 2.0, dtype=np.float32))
        g = read_netcdf3(p, "sst")
        assert g.values.shape == (3, 4)

    def test_unknown_variable(self, tmp_path):
        p = tmp_path / "s.nc"
        self._write(p, np.zeros((1, 3, 4), dtype=np.float32))
        with pytest.raises(ValueError, match="variable"):
            read_netcdf3(p, "nope")


class TestNpy:
    def test_cell_registered_extent(self, tmp_path):
        a = np.arange(8, dtype=np.int16).reshape(2, 4)
        p = tmp_path / "a.npy"
        np.save(p, a)
        g = read_npy(p, {"lat": [-90, 90], "lon": [0, 360]})
        assert g.lat.tolist() == [-45, 45]
        assert g.lon.tolist() == [-135, -45, 45, 135]
        assert g.values[0].tolist() == [2, 3, 0, 1]  # row 0 is the southern row

    def test_needs_extent(self, tmp_path):
        p = tmp_path / "a.npy"
        np.save(p, np.zeros((2, 2)))
        with pytest.raises(ValueError, match="lat"):
            read_npy(p, {})

    def test_fill_value(self, tmp_path):
        p = tmp_path / "a.npy"
        np.save(p, np.array([[1, -32768]], dtype=np.int16))
        g = read_npy(p, {"lat": [-90, 90], "lon": [-180, 180], "fill": -32768})
        assert np.isnan(g.values[0, 1])


class TestReadDataset:
    def test_split_rule_sets_land(self, tmp_path):
        p = tmp_path / "a.npy"
        np.save(p, np.array([[-5.0, 0.0, 3.0, 10.0]]))
        e = _entry("npy", grid={"lat": [-90, 90], "lon": [-180, 180]}, class_rule={"split_at": 0.0})
        g = read_dataset(e, p, "v")
        assert g.land.tolist() == [[False, False, True, True]]

    def test_negate_does_not_change_land(self, tmp_path):
        p = tmp_path / "a.npy"
        np.save(p, np.array([[-5.0, 3.0]]))
        e = _entry("npy", grid={"lat": [-90, 90], "lon": [-180, 180]}, class_rule={"split_at": 0.0})
        g = read_dataset(e, p, "v", transform="negate")
        assert g.values.tolist() == [[5.0, -3.0]]
        assert g.land.tolist() == [[False, True]]

    def test_missing_is_land(self, tmp_path):
        p = tmp_path / "a.npy"
        np.save(p, np.array([[np.nan, 3.0]]))
        e = _entry("npy", grid={"lat": [-90, 90], "lon": [-180, 180]}, class_rule={"missing_is_land": True})
        g = read_dataset(e, p, "v")
        assert g.land.tolist() == [[True, False]]

    def test_kit_design(self):
        e = _entry("kit-design", kind="packaged", class_rule={"kit_mask": True})
        g = read_dataset(e, None, "color")
        assert g.on_kit_grid and g.values.shape == (80, 128)
        assert g.categories[int(g.values[0, 0])].startswith("lego_")


def _write_nd(path, dims, data, dtype="f4", fill=None, scale=None, units="degree_C", name="ssta"):
    """A netCDF-3 file with variable ``name`` over ``dims`` (name, size) ending in lat, lon."""
    f = netcdf_file(str(path), "w")
    for dn, size in dims:
        f.createDimension(dn, size)
    lat = f.createVariable("lat", "f4", ("lat",))
    lat[:] = np.linspace(-10, 10, dict(dims)["lat"])
    lon = f.createVariable("lon", "f4", ("lon",))
    lon[:] = np.linspace(-180, 180, dict(dims)["lon"], endpoint=False)  # no wrap shift
    v = f.createVariable(name, dtype, tuple(d for d, _ in dims))
    if fill is not None:
        v._FillValue = np.array(fill, dtype=dtype)
    if scale is not None:
        v.scale_factor = np.float32(scale)
        v.add_offset = np.float32(0.0)
    v.units = units
    v[:] = data
    f.close()


class TestNetcdf3PerMonth:
    """ERSST v5 per-month files: ssta(time=1, lev=1, lat, lon), _FillValue -999 (009 R2)."""

    DIMS = [("time", 1), ("lev", 1), ("lat", 3), ("lon", 4)]

    def test_singleton_leading_axes_read_as_2d(self, tmp_path):
        data = np.arange(12, dtype=np.float32).reshape(1, 1, 3, 4)
        p = tmp_path / "m.nc"
        _write_nd(p, self.DIMS, data, fill=-999.0)
        g = read_netcdf3(p, "ssta")
        assert g.values.shape == (3, 4)
        assert g.values[0].tolist() == [0, 1, 2, 3]
        assert g.units == "degree_C"

    def test_fill_value_is_nan(self, tmp_path):
        data = np.ones((1, 1, 3, 4), dtype=np.float32)
        data[0, 0, 1, 2] = -999.0
        p = tmp_path / "m.nc"
        _write_nd(p, self.DIMS, data, fill=-999.0)
        g = read_netcdf3(p, "ssta")
        assert np.isnan(g.values[1, 2])
        assert np.isfinite(g.values).sum() == 11

    def test_packed_int16_fill_then_scale(self, tmp_path):
        data = np.array([-250, -999, 0, 493] * 3, dtype=np.int16).reshape(1, 1, 3, 4)
        p = tmp_path / "m.nc"
        _write_nd(p, self.DIMS, data, dtype="i2", fill=-999, scale=0.01)
        g = read_netcdf3(p, "ssta")
        assert np.isnan(g.values[0, 1])
        assert np.allclose(g.values[0, [0, 2, 3]], [-2.5, 0.0, 4.93], atol=1e-6)

    def test_larger_leading_axis_names_dimensions(self, tmp_path):
        dims = [("time", 2), ("lev", 1), ("lat", 3), ("lon", 4)]
        p = tmp_path / "m.nc"
        _write_nd(p, dims, np.zeros((2, 1, 3, 4), dtype=np.float32))
        with pytest.raises(ValueError, match="time=2, lev=1"):
            read_netcdf3(p, "ssta")

    def test_3d_single_and_annual_mean_unchanged(self, tmp_path):
        p1 = tmp_path / "one.nc"
        _write_nd(p1, [("time", 1), ("lat", 3), ("lon", 4)], np.full((1, 3, 4), 2.0, np.float32))
        assert read_netcdf3(p1, "ssta").values.shape == (3, 4)
        p12 = tmp_path / "twelve.nc"
        data = np.ones((12, 3, 4), np.float32) * np.arange(12, dtype=np.float32)[:, None, None]
        _write_nd(p12, [("time", 12), ("lat", 3), ("lon", 4)], data)
        g = read_netcdf3(p12, "ssta", reduce="annual-mean")
        assert np.allclose(g.values, 5.5)

    def test_annual_mean_on_one_month_keeps_error(self, tmp_path):
        p = tmp_path / "m.nc"
        _write_nd(p, self.DIMS, np.zeros((1, 1, 3, 4), dtype=np.float32))
        with pytest.raises(ValueError, match="annual-mean needs 12 months, found 1"):
            read_netcdf3(p, "ssta", reduce="annual-mean")

    def test_netcdf4_signature_rejected(self, tmp_path):
        p = tmp_path / "n4.nc"
        p.write_bytes(b"\x89HDF\r\n\x1a\n" + b"\0" * 64)
        with pytest.raises(ValueError, match=r"not a netCDF-3 classic file \(netCDF-4/HDF5 signature\)"):
            read_netcdf3(p, "ssta")

    def test_other_junk_rejected(self, tmp_path):
        p = tmp_path / "junk.nc"
        p.write_bytes(b"<html>not found</html>")
        with pytest.raises(ValueError, match="not a netCDF-3 classic file"):
            read_netcdf3(p, "ssta")


class TestEnsoFixtures:
    """The derived per-month fixtures read through the registry (feature 009, FR-002, FR-003)."""

    @pytest.mark.parametrize("dataset_id", ["ersst-v5-1997-12", "ersst-v5-1988-12"])
    def test_fixture_reads_as_one_field(self, fixture_registry, dataset_id):
        from lego_image_processor.datasets import get_entry

        path = fixture_registry.place(dataset_id)
        g = read_dataset(get_entry(dataset_id), path, "ssta")
        assert g.values.shape == (89, 180)
        assert int(g.land.sum()) == 5032
        assert int(np.isnan(g.values).sum()) == 5032
        assert np.nanmax(np.abs(g.values)) <= 5.0
