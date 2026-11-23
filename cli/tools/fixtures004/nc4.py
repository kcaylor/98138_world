"""A minimal netCDF-4 (HDF5) writer for test fixtures (feature 013), using h5py.

Object modification times are not stored, so the same input gives the same bytes. Coordinates
become HDF5 dimension scales and variables are attached to them, as the netCDF-C
library writes them, so the files read the same through h5py or netCDF tools.
Not affiliated with or endorsed by The LEGO Group.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

import numpy as np


def write_netcdf4(path: Path, coords: Mapping[str, np.ndarray],
                  variables: Mapping[str, Tuple[Sequence[str], np.ndarray, Dict[str, Any]]],
                  attrs: Optional[Mapping[str, Any]] = None, compress: bool = True,
                  scalars: Optional[Mapping[str, Dict[str, Any]]] = None) -> Path:
    """Write ``coords`` (1-D dimension scales), ``variables`` (``name -> (dims, data, attrs)``) and
    ``scalars`` (attribute-only variables such as a CF ``crs``) to ``path``."""
    import h5py

    path = Path(path)
    with h5py.File(str(path), "w", track_order=True) as f:
        for k, v in (attrs or {}).items():
            f.attrs[k] = v
        for name, values in coords.items():
            d = f.create_dataset(name, data=np.asarray(values), track_times=False)
            d.make_scale(name)
        for name, a in (scalars or {}).items():
            d = f.create_dataset(name, data=np.int32(0), track_times=False)
            for k, v in a.items():
                d.attrs[k] = v
        for name, (dims, data, a) in variables.items():
            data = np.asarray(data)
            kw = {"compression": "gzip", "compression_opts": 4, "chunks": True} if compress and data.ndim > 1 else {}
            fill = a.get("_FillValue")
            if fill is not None:
                kw["fillvalue"] = np.asarray(fill, dtype=data.dtype).ravel()[0]
            d = f.create_dataset(name, data=data, track_times=False, **kw)
            for k, v in a.items():
                d.attrs[k] = np.asarray(v, dtype=data.dtype) if k == "_FillValue" else v
            for i, dim in enumerate(dims):
                if dim in f:
                    d.dims[i].attach_scale(f[dim])
    return path
