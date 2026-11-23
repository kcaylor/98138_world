"""Strip GeoTIFF reader with block means (feature 012, FR-003; research R1)."""

import struct

import numpy as np
import pytest
from PIL import Image, TiffImagePlugin

from lego_image_processor.datasets.geotiff import geotiff_extent, read_geotiff, read_layout


def _write(path, codes, *, west=-180.0, north=80.0, step=1.0, compression="tiff_lzw",
           rows_per_strip=None, mode="I;16", georef=True, predictor=None):
    ifd = TiffImagePlugin.ImageFileDirectory_v2()
    if georef:
        ifd[33550] = (step, step, 0.0)
        ifd.tagtype[33550] = 12
        ifd[33922] = (0.0, 0.0, 0.0, west, north, 0.0)
        ifd.tagtype[33922] = 12
    if rows_per_strip is not None:
        ifd[278] = rows_per_strip
    if predictor is not None:
        ifd[317] = predictor
    dtype = {"I;16": "<u2", "F": "<f4"}[mode]
    im = Image.fromarray(np.ascontiguousarray(codes.astype(dtype)), mode=mode)
    kw = {"compression": compression} if compression else {}
    im.save(str(path), tiffinfo=ifd, **kw)
    return path


def _codes(h=6, w=8):
    return (np.arange(h * w).reshape(h, w) * 10).astype(np.uint16)


@pytest.mark.parametrize("compression,rps", [(c, r) for c in ("tiff_lzw", "tiff_adobe_deflate")
                                             for r in (1, 3, None)] + [(None, None)])
def test_block_1_round_trip(tmp_path, compression, rps):
    c = _codes()
    p = _write(tmp_path / "a.tif", c, compression=compression, rows_per_strip=rps)
    g = read_geotiff(p)
    # rows south to north after normalise
    assert np.array_equal(g.values, c[::-1].astype(float))
    assert np.allclose(g.lat, [74.5, 75.5, 76.5, 77.5, 78.5, 79.5])
    assert np.allclose(g.lon, -180 + 0.5 + np.arange(8))


def _write_raw_strips(path, codes, rps, endian="<"):
    """An uncompressed multi-strip GeoTIFF written by hand (Pillow writes one strip)."""
    h, w = codes.shape
    strips = [codes[r:r + rps].astype(endian + "u2").tobytes() for r in range(0, h, rps)]
    tags = [(256, 4, [w]), (257, 4, [h]), (258, 3, [16]), (259, 3, [1]), (262, 3, [1]),
            (273, 4, None), (277, 3, [1]), (278, 4, [rps]), (279, 4, [len(s) for s in strips]),
            (339, 3, [1]), (33550, 12, [1.0, 1.0, 0.0]), (33922, 12, [0, 0, 0, -180.0, 80.0, 0])]
    fmt = {3: "H", 4: "I", 12: "d"}
    extra_at = 8 + 2 + 12 * len(tags) + 4
    blobs, entries = b"", []
    data_at = extra_at + sum(len(v) * struct.calcsize(fmt[t]) for _, t, v in tags if v and
                             len(v) * struct.calcsize(fmt[t]) > 4) + 4 * len(strips) * (len(strips) > 1)
    offsets, pos = [], data_at
    for st in strips:
        offsets.append(pos)
        pos += len(st)
    for tag, typ, vals in tags:
        vals = offsets if tag == 273 else vals
        raw = struct.pack(endian + fmt[typ] * len(vals), *vals)
        if len(raw) <= 4:
            entries.append(struct.pack(endian + "HHI", tag, typ, len(vals)) + raw.ljust(4, b"\0"))
        else:
            entries.append(struct.pack(endian + "HHII", tag, typ, len(vals), extra_at + len(blobs)))
            blobs += raw
    order = b"II" if endian == "<" else b"MM"
    head = order + struct.pack(endian + "HI", 42, 8)
    body = struct.pack(endian + "H", len(tags)) + b"".join(entries) + struct.pack(endian + "I", 0)
    path.write_bytes(head + body + blobs + b"".join(strips))
    return path


@pytest.mark.parametrize("endian", ["<", ">"])
def test_uncompressed_multistrip(tmp_path, endian):
    c = _codes(7, 5)
    p = _write_raw_strips(tmp_path / "u.tif", c, rps=2, endian=endian)
    lay = read_layout(p)
    assert lay.rows_per_strip == 2 and len(lay.offsets) == 4
    assert np.array_equal(read_geotiff(p).values, c[::-1].astype(float))
    g = read_geotiff(p, block=3)
    assert g.values.shape == (3, 2)


def test_predictor_lzw(tmp_path):
    c = _codes()
    p = _write(tmp_path / "p.tif", c, predictor=2)
    assert read_layout(p).predictor in (1, 2)
    assert np.array_equal(read_geotiff(p).values, c[::-1].astype(float))


def test_block_means_of_valid_pixels_scale_and_fill(tmp_path):
    c = np.array([[10, 20, 65535, 65535],
                  [30, 40, 65535, 65535],
                  [100, 65535, 7, 9],
                  [65535, 65535, 65532, 65535]], dtype=np.uint16)
    p = _write(tmp_path / "b.tif", c, west=0.0, north=2.0, step=0.5, rows_per_strip=1)
    g = read_geotiff(p, block=2, scale_factor=0.1, valid_max=65499, fill=65535)
    # north row first in the file; values are south to north
    north, south = g.values[1], g.values[0]
    assert north[0] == pytest.approx(2.5) and np.isnan(north[1])
    assert south[0] == pytest.approx(10.0) and south[1] == pytest.approx(0.8)
    assert np.allclose(g.lat, [0.5, 1.5]) and np.allclose(g.lon, [0.5, 1.5])


def test_partial_edge_blocks(tmp_path):
    c = np.ones((5, 5), dtype=np.uint16)
    g = read_geotiff(_write(tmp_path / "e.tif", c, west=0.0, north=5.0), block=2)
    assert g.values.shape == (3, 3) and np.all(g.values == 1)
    assert g.lat[0] == pytest.approx(0.5) and g.lon[-1] == pytest.approx(4.5)


def test_float_samples(tmp_path):
    c = np.array([[1.5, np.nan], [2.5, 3.5]], dtype=np.float32)
    g = read_geotiff(_write(tmp_path / "f.tif", c, mode="F"))
    assert np.isnan(g.values[1, 1]) and g.values[0, 0] == pytest.approx(2.5)


def test_extent(tmp_path):
    p = _write(tmp_path / "x.tif", _codes(), step=0.25)
    assert geotiff_extent(p) == {"north": 80.0, "south": 78.5, "west": -180.0, "east": -178.0}


def test_errors(tmp_path):
    with pytest.raises(ValueError, match="not a GeoTIFF"):
        read_geotiff(_write(tmp_path / "n.tif", _codes(), georef=False))
    junk = tmp_path / "junk.tif"
    junk.write_bytes(b"hello world")
    with pytest.raises(ValueError, match="not a TIFF"):
        read_geotiff(junk)
    big = tmp_path / "big.tif"
    big.write_bytes(b"II" + struct.pack("<H", 43) + b"\0" * 12)
    with pytest.raises(ValueError, match="BigTIFF"):
        read_geotiff(big)
    tiled = tmp_path / "t.tif"
    _write(tiled, _codes(32, 32))
    data = bytearray(tiled.read_bytes())
    # rename the RowsPerStrip tag (278) to TileWidth (322) in place: the reader must refuse tiles
    off = struct.unpack("<I", data[4:8])[0]
    n = struct.unpack("<H", data[off:off + 2])[0]
    for i in range(n):
        e = off + 2 + 12 * i
        if struct.unpack("<H", data[e:e + 2])[0] == 278:
            data[e:e + 2] = struct.pack("<H", 322)
    tiled.write_bytes(bytes(data))
    with pytest.raises(ValueError, match="tiled"):
        read_geotiff(tiled)
    with pytest.raises(ValueError, match="block"):
        read_geotiff(_write(tmp_path / "ok.tif", _codes()), block=0)


def test_fixture_reads_as_two_degree_grid():
    from pathlib import Path

    p = Path(__file__).resolve().parents[2] / "fixtures" / "datasets" / "mod17a3_npp_1deg.tif"
    lay = read_layout(p)
    assert (lay.width, lay.height, lay.compression) == (360, 140, 5)
    g = read_geotiff(p, block=2, scale_factor=0.1, valid_max=65499, fill=65535)
    assert g.values.shape == (70, 180)
    v = g.values[np.isfinite(g.values)]
    assert 0 <= v.min() and v.max() < 3000 and v.size > 1500
