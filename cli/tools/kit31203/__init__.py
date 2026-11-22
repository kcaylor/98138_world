"""Maintainer tool: extract kit 31203 reference data from the pinned instructions PDF.

Not shipped in the ``lego_image_processor`` package. Requires the optional Poetry group
``maintainer`` (pypdf). Run from ``cli/``::

    poetry run python -m kit31203 extract [--pdf PATH] [--check]

Not affiliated with or endorsed by The LEGO Group.
"""

from lego_image_processor.kit.source import PINNED_SHA256, PINNED_URL  # noqa: F401

PDF_CACHE_NAME = "31203-instructions-6372756.pdf"
INVENTORY_PAGE = 159
