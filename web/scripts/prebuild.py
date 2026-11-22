#!/usr/bin/env python3
"""Build every 98138.world map variant and download into a static output directory.

Same as ``python -m web98138.prebuild``; see ``--help``. Needs the CLI package
(``pip install ../cli``). Not affiliated with or endorsed by The LEGO Group.
"""

import sys

from web98138.prebuild import main

if __name__ == "__main__":
    sys.exit(main())
