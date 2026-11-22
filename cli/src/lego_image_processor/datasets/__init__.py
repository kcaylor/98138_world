"""Canonical datasets: registry, verified per-user cache and readers (feature 004).

Only ``fetch`` opens the network. Not affiliated with or endorsed by The LEGO Group.
"""

from .cache import (ChecksumMismatchError, DatasetError, DatasetNotCachedError, FetchError,
                    cache_root, cached_path, fetch, is_cached, resolve, sha256_file, verify)
from .grid import SourceGrid
from .readers import read_dataset
from .registry import DatasetEntry, Registry, RegistryError, get_entry, load_registry

__all__ = [
    "DatasetEntry", "Registry", "RegistryError", "load_registry", "get_entry",
    "cache_root", "cached_path", "is_cached", "fetch", "verify", "resolve", "sha256_file",
    "SourceGrid", "read_dataset",
    "DatasetError", "DatasetNotCachedError", "ChecksumMismatchError", "FetchError",
]
