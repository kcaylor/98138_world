"""Map template maintainer tool (feature 016): ``python -m maptemplates`` from ``cli/`` with
``PYTHONPATH=tools``. Not packaged.

Commands (specs/016-map-templates/contracts/template-file.md): ``generate``, ``review``,
``write`` and ``build --check`` (template layouts, feature 016 Phase 3) and ``kit-golden`` (digests
of every kit 31203 output, research R9); ``ice-mask`` comes in a later phase. Every command prints
the disclaimer last.

Modules: ``generate`` (the layout from ETOPO 2022 with pyproj, built on the projection study;
review flags; the template document), ``review`` (review sheet PNG and flags JSON), ``document``
(the template file writer, corrections, confirmation, differences), ``golden`` (kit digests),
``testing`` (numpy-only test helpers: the synthetic test template, ``confirmed_copy``,
``use_template_dir``; shared with the web tests). Not affiliated with or endorsed by The LEGO Group.
"""
