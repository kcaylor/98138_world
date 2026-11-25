"""98138.world web site (feature 008): pick a bundled map and a frame combination, see the stud
preview, download the layout, parts lists, marketplace files and build sheets.

The files are built ahead of time by :mod:`web98138.prebuild` with the CLI library
(``lego_image_processor``); the service (:mod:`web98138.app`) serves them and never imports the
library. Not affiliated with or endorsed by The LEGO Group.
"""

__version__ = "0.1.0"

DISCLAIMER = "Not affiliated with or endorsed by The LEGO Group."
REPO_URL = "https://github.com/kcaylor/98138_world"
SITE_HOST = "98138.world"
MAP_IDS = ("official-31203", "official-31203-bathymetry", "ocean-sst", "land-elevation", "ocean-el-nino",
           "ocean-la-nina")
COMBINATIONS = ("A", "B", "C", "D", "E")  # D and E (feature 010) are not in the building instructions
