"""Fixture tool for the ERSST v5 per-month files (feature 009, research R6; data-model.md Fixture).

A synthetic 4-D source stands in for the real NCEI file; no network. Not affiliated with or
endorsed by The LEGO Group.
"""

import hashlib
import json

import numpy as np
from scipy.io import netcdf_file

from fixtures004.make_fixtures import make_ersst_month


def _write_source(path):
    f = netcdf_file(str(path), "w")
    for name, size in (("time", 1), ("lev", 1), ("lat", 5), ("lon", 6)):
        f.createDimension(name, size)
    t = f.createVariable("time", "f4", ("time",))
    t[:] = [0.0]
    t.units = "days since 1854-01-01"
    lev = f.createVariable("lev", "f4", ("lev",))
    lev[:] = [0.0]
    lat = f.createVariable("lat", "f4", ("lat",))
    lat[:] = np.linspace(-8, 8, 5)
    lon = f.createVariable("lon", "f4", ("lon",))
    lon[:] = np.arange(0, 360, 60)
    data = np.linspace(-3.0, 4.0, 30, dtype=np.float32).reshape(1, 1, 5, 6)
    data[0, 0, 0, 0] = -999.0
    for name in ("sst", "ssta"):
        v = f.createVariable(name, "f4", ("time", "lev", "lat", "lon"))
        v._FillValue = np.float32(-999.0)
        v.units = "degree_C"
        v[:] = data
    f.close()
    return data


def _stub_registry(tmp_path, monkeypatch, src):
    from lego_image_processor.datasets import registry as reg

    data = json.loads(reg.REGISTRY_PATH.read_text(encoding="utf-8"))
    for row in data["datasets"]:
        if row["id"] == "ersst-v5-1997-12":
            row.update(size=src.stat().st_size, sha256=hashlib.sha256(src.read_bytes()).hexdigest())
    p = tmp_path / "datasets.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    monkeypatch.setattr(reg, "REGISTRY_PATH", p)


def test_make_ersst_month(tmp_path, monkeypatch):
    from lego_image_processor.datasets import cached_path, get_entry

    staging = tmp_path / "staging.nc"
    data = _write_source(staging)
    _stub_registry(tmp_path, monkeypatch, staging)
    cache = tmp_path / "cache"
    dest = cached_path(get_entry("ersst-v5-1997-12"), cache)
    dest.parent.mkdir(parents=True)
    dest.write_bytes(staging.read_bytes())
    out = tmp_path / "out"
    out.mkdir()

    p = make_ersst_month("ersst-v5-1997-12", cache, out)

    assert p.name == "ersst_v5_199712_ssta.nc"
    with netcdf_file(str(p), "r", mmap=False) as f:
        assert dict(f.dimensions) == {"time": 1, "lev": 1, "lat": 5, "lon": 6}
        assert {"time", "lev", "lat", "lon", "ssta"} == set(f.variables)
        v = f.variables["ssta"]
        assert v.dimensions == ("time", "lev", "lat", "lon")
        assert v.data.dtype == np.dtype(">i2")
        assert float(v.scale_factor) == np.float32(0.01)
        assert int(v._FillValue) == -999
        units = v.units.decode() if isinstance(v.units, bytes) else v.units
        assert units == "degree_C"
        packed = np.array(v[:])
    assert packed[0, 0, 0, 0] == -999
    assert np.allclose(packed[0, 0].ravel()[1:] * 0.01, data[0, 0].ravel()[1:], atol=0.0051)

    meta = json.loads((out / "ersst_v5_199712_ssta.source.json").read_text(encoding="utf-8"))
    for key in ("fixture", "dataset", "version", "source_sha256", "source_url", "method", "license",
                "citation", "doi", "generator", "disclaimer", "units", "sha256"):
        assert key in meta, key
    assert meta["fixture"] == p.name and meta["dataset"] == "ersst-v5-1997-12"
    assert meta["sha256"] == hashlib.sha256(p.read_bytes()).hexdigest()
    assert "Not affiliated with or endorsed by The LEGO Group" in meta["disclaimer"]
