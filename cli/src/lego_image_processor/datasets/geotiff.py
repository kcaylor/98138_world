"""A GeoTIFF reader that never decodes the whole image at once (feature 012, research R1).

Supports classic (not Big) TIFF, one band, strips (any rows per strip), compression none, LZW or
Deflate (with or without a predictor), 8/16/32-bit integer or float samples, georeferenced by
ModelTiepoint (33922) and ModelPixelScale (33550) in degrees. The header and the first IFD are
parsed here; each band of rows is decoded by handing Pillow (its bundled libtiff) a minimal
in-memory TIFF that holds only the strips of that band. With ``block = b`` the result is the mean
of the valid pixels of each ``b`` x ``b`` block, so memory stays at a few bands of rows.

Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

from .grid import SourceGrid, normalise

_TYPES = {1: ("B", 1), 2: ("s", 1), 3: ("H", 2), 4: ("I", 4), 5: ("II", 8), 6: ("b", 1),
          7: ("B", 1), 8: ("h", 2), 9: ("i", 4), 10: ("ii", 8), 11: ("f", 4), 12: ("d", 8),
          16: ("Q", 8)}
_COMPRESSIONS = {1: "none", 5: "LZW", 8: "Deflate", 32946: "Deflate"}
_PILLOW_MODES = {(1, 8): "L", (1, 16): "I;16", (2, 16): "I;16S", (2, 32): "I", (3, 32): "F"}
_NP_DTYPES = {(1, 8): "u1", (1, 16): "u2", (2, 8): "i1", (2, 16): "i2", (1, 32): "u4",
              (2, 32): "i4", (3, 32): "f4", (3, 64): "f8"}


@dataclass
class TiffLayout:
    endian: str
    width: int
    height: int
    bits: int
    sample_format: int
    compression: int
    predictor: int
    rows_per_strip: int
    offsets: Tuple[int, ...]
    counts: Tuple[int, ...]
    lon0: float
    lat0: float
    dlon: float
    dlat: float
    nodata: Optional[float] = None


def _read_ifd(fh, endian: str) -> Dict[int, tuple]:
    head = fh.read(8)
    if len(head) < 8:
        raise ValueError("not a TIFF file (too short)")
    magic = struct.unpack(endian + "H", head[2:4])[0]
    if magic == 43:
        raise ValueError("BigTIFF is not supported; use a classic TIFF")
    if magic != 42:
        raise ValueError("not a TIFF file (bad magic number)")
    off = struct.unpack(endian + "I", head[4:8])[0]
    fh.seek(off)
    n = struct.unpack(endian + "H", fh.read(2))[0]
    entries = [fh.read(12) for _ in range(n)]
    tags: Dict[int, tuple] = {}
    for e in entries:
        tag, typ, count = struct.unpack(endian + "HHI", e[:8])
        if typ not in _TYPES:
            continue
        code, width = _TYPES[typ]
        size = width * count
        if size <= 4:
            data = e[8:8 + size]
        else:
            ptr = struct.unpack(endian + "I", e[8:12])[0]
            here = fh.tell()
            fh.seek(ptr)
            data = fh.read(size)
            fh.seek(here)
        if typ == 2:
            tags[tag] = (data.rstrip(b"\x00").decode("ascii", "replace"),)
        elif typ in (5, 10):
            v = struct.unpack(endian + code[0] * (2 * count), data)
            tags[tag] = tuple(v[i] / v[i + 1] if v[i + 1] else 0.0 for i in range(0, len(v), 2))
        else:
            tags[tag] = struct.unpack(endian + code * count, data)
    return tags


def read_layout(path) -> TiffLayout:
    """Parse the header and the first IFD; raise ``ValueError`` for anything unsupported."""
    with open(path, "rb") as fh:
        order = fh.read(2)
        if order not in (b"II", b"MM"):
            raise ValueError(f"{path}: not a TIFF file")
        endian = "<" if order == b"II" else ">"
        fh.seek(0)
        try:
            tags = _read_ifd(fh, endian)
        except (struct.error, ValueError) as exc:
            raise ValueError(f"{path}: {exc}") from exc

    def one(tag, default=None):
        v = tags.get(tag)
        return v[0] if v else default

    if 322 in tags or 324 in tags:
        raise ValueError(f"{path}: tiled TIFF is not supported (strips only)")
    if one(277, 1) != 1:
        raise ValueError(f"{path}: {one(277)} samples per pixel; only single-band files are supported")
    compression = one(259, 1)
    if compression not in _COMPRESSIONS:
        raise ValueError(f"{path}: TIFF compression {compression} is not supported "
                         f"(supported: none, LZW, Deflate)")
    bits = one(258, 1)
    fmt = one(339, 1)
    if (fmt, bits) not in _NP_DTYPES:
        raise ValueError(f"{path}: {bits}-bit samples of format {fmt} are not supported")
    if 33922 not in tags or 33550 not in tags:
        raise ValueError(f"{path}: not a GeoTIFF (ModelTiepoint and ModelPixelScale tags missing)")
    tie, scale = tags[33922], tags[33550]
    if len(tie) < 6 or tie[0] != 0 or tie[1] != 0:
        raise ValueError(f"{path}: GeoTIFF tiepoint must refer to pixel (0, 0)")
    if 273 not in tags or 279 not in tags:
        raise ValueError(f"{path}: TIFF has no strips")
    width, height = one(256), one(257)
    nodata = None
    if 42113 in tags:
        try:
            nodata = float(tags[42113][0])
        except ValueError:
            nodata = None
    return TiffLayout(endian=endian, width=width, height=height, bits=bits, sample_format=fmt,
                      compression=compression, predictor=one(317, 1),
                      rows_per_strip=min(one(278, height), height), offsets=tuple(tags[273]),
                      counts=tuple(tags[279]), lon0=float(tie[3]), lat0=float(tie[4]),
                      dlon=float(scale[0]), dlat=float(scale[1]), nodata=nodata)


def _mini_tiff(lay: TiffLayout, strips: List[bytes], rows: int) -> bytes:
    """A little-endian TIFF with only these strips (``rows`` rows); strip bytes are unchanged."""
    entries = [(256, 4, [lay.width]), (257, 4, [rows]), (258, 3, [lay.bits]),
               (259, 3, [lay.compression]), (262, 3, [1]), (273, 4, [0] * len(strips)),
               (277, 3, [1]), (278, 4, [lay.rows_per_strip]), (279, 4, [len(s) for s in strips]),
               (284, 3, [1]), (339, 3, [lay.sample_format])]
    if lay.predictor != 1:
        entries.append((317, 3, [lay.predictor]))
    entries.sort()

    def width(typ):
        return 2 if typ == 3 else 4

    extra_start = 8 + 2 + 12 * len(entries) + 4
    extra_len = sum(len(v) * width(t) for _, t, v in entries if len(v) * width(t) > 4)
    pos = extra_start + extra_len
    offsets = []
    for s in strips:
        offsets.append(pos)
        pos += len(s)
    ifd, extras = [struct.pack("<H", len(entries))], []
    ptr = extra_start
    for tag, typ, vals in entries:
        if tag == 273:
            vals = offsets
        raw = struct.pack("<" + ("H" if typ == 3 else "I") * len(vals), *vals)
        if len(raw) <= 4:
            ifd.append(struct.pack("<HHI", tag, typ, len(vals)) + raw.ljust(4, b"\x00"))
        else:
            ifd.append(struct.pack("<HHII", tag, typ, len(vals), ptr))
            extras.append(raw)
            ptr += len(raw)
    ifd.append(struct.pack("<I", 0))
    return b"II*\x00" + struct.pack("<I", 8) + b"".join(ifd) + b"".join(extras) + b"".join(strips)


def _decode_rows(fh, lay: TiffLayout, r0: int, r1: int) -> np.ndarray:
    """Rows ``r0..r1-1`` as a NumPy array (native byte order)."""
    from PIL import Image

    rps = lay.rows_per_strip
    s0, s1 = r0 // rps, (r1 - 1) // rps
    strips = []
    for s in range(s0, s1 + 1):
        fh.seek(lay.offsets[s])
        strips.append(fh.read(lay.counts[s]))
    rows = min((s1 + 1) * rps, lay.height) - s0 * rps
    dtype = np.dtype(_NP_DTYPES[(lay.sample_format, lay.bits)])
    if lay.compression == 1 and lay.predictor == 1:
        a = np.frombuffer(b"".join(strips), dtype=dtype.newbyteorder(lay.endian))
        a = a[:rows * lay.width].reshape(rows, lay.width)
    else:
        if lay.endian == ">":
            raise ValueError("compressed big-endian TIFF is not supported")
        if (lay.sample_format, lay.bits) not in _PILLOW_MODES:
            raise ValueError(f"compressed {lay.bits}-bit samples of format {lay.sample_format} are "
                             "not supported")
        im = Image.open(io.BytesIO(_mini_tiff(lay, strips, rows)))
        im.load()
        a = np.asarray(im)
        if a.shape != (rows, lay.width):
            raise ValueError(f"decoded strip block has shape {a.shape}, expected {(rows, lay.width)}")
    lo = r0 - s0 * rps
    return np.asarray(a[lo:lo + (r1 - r0)], dtype=dtype)


def read_geotiff(path, *, block: int = 1, scale_factor: Optional[float] = None,
                 add_offset: Optional[float] = None, valid_min: Optional[float] = None,
                 valid_max: Optional[float] = None, fill: Optional[float] = None) -> SourceGrid:
    """Read band 1 of a strip GeoTIFF as a :class:`SourceGrid`.

    A raw value is valid when it is finite, not ``fill`` (nor the file's GDAL nodata tag), and
    within ``[valid_min, valid_max]``. With ``block`` > 1, each output cell is the mean of the
    valid raw values in a ``block`` x ``block`` block of pixels (edge blocks may be smaller), NaN if
    it has none; ``scale_factor`` and ``add_offset`` are applied after the mean (they are linear).
    """
    block = int(block)
    if block < 1:
        raise ValueError("block must be >= 1")
    lay = read_layout(path)
    W, H = lay.width, lay.height
    nby, nbx = -(-H // block), -(-W // block)
    out = np.full((nby, nbx), np.nan)
    pad = nbx * block - W
    nodata = fill if fill is not None else lay.nodata
    with open(path, "rb") as fh:
        for by in range(nby):
            r0, r1 = by * block, min((by + 1) * block, H)
            raw = _decode_rows(fh, lay, r0, r1).astype(np.float64)
            ok = np.isfinite(raw)
            if nodata is not None:
                ok &= raw != nodata
            if lay.nodata is not None and fill is not None:
                ok &= raw != lay.nodata
            if valid_min is not None:
                ok &= raw >= valid_min
            if valid_max is not None:
                ok &= raw <= valid_max
            v = np.where(ok, raw, 0.0)
            if pad:
                v = np.pad(v, ((0, 0), (0, pad)))
                ok = np.pad(ok, ((0, 0), (0, pad)))
            s = v.reshape(r1 - r0, nbx, block).sum(axis=(0, 2))
            n = ok.reshape(r1 - r0, nbx, block).sum(axis=(0, 2))
            with np.errstate(invalid="ignore", divide="ignore"):
                out[by] = np.where(n > 0, s / np.maximum(n, 1), np.nan)
    if scale_factor is not None:
        out = out * float(scale_factor)
    if add_offset is not None:
        out = out + float(add_offset)
    d_lat, d_lon = lay.dlat * block, lay.dlon * block
    lat = lay.lat0 - (np.arange(nby) + 0.5) * d_lat
    lon = lay.lon0 + (np.arange(nbx) + 0.5) * d_lon
    if H % block:  # the last block row is shorter: centre it on its own rows
        lat[-1] = lay.lat0 - (r0 + (H - r0) / 2.0) * lay.dlat
    if W % block:
        c0 = (nbx - 1) * block
        lon[-1] = lay.lon0 + (c0 + (W - c0) / 2.0) * lay.dlon
    values, lat, lon = normalise(out, lat, lon)
    return SourceGrid(values=values, lat=lat, lon=lon)


def geotiff_extent(path) -> Dict[str, float]:
    """Edges of the georeferenced image: ``{"north", "south", "west", "east"}`` (degrees)."""
    lay = read_layout(Path(path))
    return {"north": lay.lat0, "south": lay.lat0 - lay.height * lay.dlat, "west": lay.lon0,
            "east": lay.lon0 + lay.width * lay.dlon}
