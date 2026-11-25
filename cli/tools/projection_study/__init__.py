"""Projection study (maintainer research tool, not packaged).

Rasterises world map projections onto rectangular boards of whole 16×16 LEGO modules and reports
how each one fills the board: land, ocean and off-globe ("margin") studs, outline length, module
use and area distortion. It produced the 2026-11-22 study behind constitution 3.0.0 (Principle I,
map templates) and is the starting point for the template-building tool of feature 016.

Run from ``cli/`` with ``PYTHONPATH=tools python -m projection_study --help``; see README.md.
"""
