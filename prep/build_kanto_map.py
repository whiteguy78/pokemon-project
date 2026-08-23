"""
Draws Kanto's map from scratch (Kanto only -- every other region uses a
traced real map instead; see prep/pixelate_map.py and data/maps/README.md).

Generates the Kanto pixel map SVG (and a scaled-up calibration version with
a coordinate grid overlay) from data/maps/kanto_pins.json.

The odd part of this one: the landmass shape is derived from the pins
themselves (an elliptical blob sized to comfortably contain them, plus a
small separate island for Cinnabar/Seafoam) rather than hand-drawn ASCII
art. In other words, we place the dots first and then grow an island
underneath them -- that guarantees every pin actually lands on "ground"
instead of floating in the water, at the cost of the coastline being a
rough approximation rather than a faithful outline. A deterministic noise
function roughs up the coastline so it reads as a map instead of a perfect
ellipse, plus shallow-water/coast/wave shading for a bit of cartographic
texture.

Two files come out:
  app/static/maps/kanto.svg              -- the one the app shows
  app/static/maps/kanto_calibration.svg  -- big version with a numbered
                                            grid + labels, for reading off
                                            coordinates when moving pins

Re-run this any time kanto_pins.json changes:
    python3 prep/build_kanto_map.py
"""
import json
from pathlib import Path

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
PINS_PATH = PROJECT_DIR / "data" / "maps" / "kanto_pins.json"
OUT_DIR = PROJECT_DIR / "app" / "static" / "maps"

CELL = 4  # size of one pixel "block" in the 0-100 viewBox -- bigger = blockier

# The whole palette. Everything drawn is one of these seven colours.
DEEP_WATER = "#3d96ba"
SHALLOW_WATER = "#5ec2e0"
WAVE_COLOR = "#79d3ee"
LAND_COLOR = "#8fc75a"
COAST_COLOR = "#7ab84e"
MOUNTAIN_COLOR = "#8a7a63"
MOUNTAIN_PEAK = "#a9977f"

# We don't have a "this is a mountain" flag in the data, so we guess from
# the location's name. Crude, but it's decoration, not data.
MOUNTAIN_HINTS = ["mt moon", "rock tunnel", "victory road", "cerulean cave", "cave"]
ISLAND_HINTS = ["cinnabar", "mansion", "seafoam"]


def load_pins():
    with open(PINS_PATH) as f:
        return json.load(f)


def cell_noise(col, row, seed=0):
    # Deterministic pseudo-random value in [0, 1) from cell coordinates --
    # same input always gives the same output, so the coastline is stable
    # across regenerations instead of reshuffling every run.
    #
    # It's just a pile of multiplying and bit-shuffling: the numbers are
    # arbitrary big primes, and the point is only that small changes in
    # the input scramble the output. Don't read meaning into them.
    n = (col * 374761393 + row * 668265263 + seed * 2147483647) & 0xffffffff
    n = (n ^ (n >> 13)) * 1274126177 & 0xffffffff
    n = n ^ (n >> 16)
    return (n & 0xffff) / 0xffff  # squash down to 0.0 - 1.0


def compute_shape_params(pins):
    # Find a centre point and a radius that comfortably contains every pin.
    # The "+ 8" is padding, so pins near the edge still sit on land rather
    # than right on the beach.
    xs = [p["x"] for p in pins.values()]
    ys = [p["y"] for p in pins.values()]
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    rx = (max(xs) - min(xs)) / 2 + 8
    ry = (max(ys) - min(ys)) / 2 + 8
    return cx, cy, rx, ry


def is_island_pin(pin):
    # Cinnabar and the Seafoam Islands are offshore, so they get their own
    # little blob rather than being swallowed by the mainland ellipse.
    return any(hint in pin["label"].lower() for hint in ISLAND_HINTS)


def ellipse_dist(mid_x, mid_y, cx, cy, rx, ry, col, row, seed):
    # Base elliptical falloff, roughed up with per-cell noise so the edge
    # is jagged/organic instead of a perfect oval.
    #
    # The result is "how far outside the ellipse is this square?" --
    # under 1 means inside (land), over 1 means outside (sea).
    d = ((mid_x - cx) / rx) ** 2 + ((mid_y - cy) / ry) ** 2
    jitter = (cell_noise(col, row, seed) - 0.5) * 0.35
    return d + jitter


def build_grid(pins):
    """Decide what colour every square of the map should be."""
    island_pins = [p for p in pins.values() if is_island_pin(p)]

    # One ellipse for the mainland, one for the little southern island.
    cx, cy, rx, ry = compute_shape_params(pins)
    icx = sum(p["x"] for p in island_pins) / len(island_pins)
    icy = sum(p["y"] for p in island_pins) / len(island_pins)

    # Mark a 3x3 patch of squares around each cave/mountain location so
    # they get drawn in rock colours.
    mountain_cells = set()
    for slug, pin in pins.items():
        if any(hint in pin["label"].lower() for hint in MOUNTAIN_HINTS):
            col, row = round(pin["x"] / CELL), round(pin["y"] / CELL)
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    mountain_cells.add((col + dc, row + dr))

    steps = int(100 / CELL)  # how many squares across and down
    land_mask = {}   # (col, row) -> True if land
    dist_mask = {}   # (col, row) -> jittered distance, for shallow-water banding

    # Pass 1: for every square, is it land or sea, and how far out is it?
    for row in range(steps):
        for col in range(steps):
            mid_x, mid_y = col * CELL + CELL / 2, row * CELL + CELL / 2
            d_main = ellipse_dist(mid_x, mid_y, cx, cy, rx, ry, col, row, seed=0)
            d_island = ellipse_dist(mid_x, mid_y, icx, icy, 6, 5, col, row, seed=1)
            # Land if it's inside EITHER blob, hence the min().
            d = min(d_main, d_island)
            dist_mask[(col, row)] = d
            land_mask[(col, row)] = d <= 1

    def neighbors(col, row):
        return [(col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)]

    # Pass 2: now that we know the shape, pick an actual colour per square.
    cells = []
    for row in range(steps):
        for col in range(steps):
            x, y = col * CELL, row * CELL
            d = dist_mask[(col, row)]

            if land_mask[(col, row)]:
                # A land square touching any sea square is coastline, and
                # gets a slightly darker green so the outline reads.
                is_coast = any(not land_mask.get(n, False) for n in neighbors(col, row))
                if (col, row) in mountain_cells:
                    color = MOUNTAIN_PEAK if cell_noise(col, row, 3) > 0.6 else MOUNTAIN_COLOR
                else:
                    color = COAST_COLOR if is_coast else LAND_COLOR
            elif d <= 1.35:
                color = SHALLOW_WATER  # a band of lighter blue near shore
            else:
                # Out at sea, sprinkle the occasional lighter square so it
                # looks like waves rather than a flat blue rectangle.
                color = WAVE_COLOR if cell_noise(col, row, 2) > 0.94 else DEEP_WATER

            cells.append((x, y, color))

    return cells


def build_land_svg_body(cells):
    # One <rect> per square. An SVG really is just text like this.
    rects = [f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" fill="{color}"/>' for x, y, color in cells]
    return "\n    ".join(rects)


def build_base_svg(cells):
    """The plain map that the app displays."""
    body = build_land_svg_body(cells)
    return f'''<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    {body}
</svg>'''


def build_calibration_svg(cells, pins):
    """The same map, but huge, with a numbered grid and every pin labelled.

    This one is a tool, not a display asset: open it, find where a pin
    should actually be, read the numbers off the gridlines, and type those
    into kanto_pins.json.
    """
    body = build_land_svg_body(cells)

    # Gridlines and their number labels, every 10 units.
    gridlines = []
    for i in range(0, 101, 10):
        gridlines.append(f'<line x1="{i}" y1="0" x2="{i}" y2="100" stroke="black" stroke-width="0.15" opacity="0.4"/>')
        gridlines.append(f'<line x1="0" y1="{i}" x2="100" y2="{i}" stroke="black" stroke-width="0.15" opacity="0.4"/>')
        gridlines.append(f'<text x="{i+0.5}" y="2.5" font-size="2" fill="black">{i}</text>')
        gridlines.append(f'<text x="0.5" y="{i+2}" font-size="2" fill="black">{i}</text>')

    # A red dot plus a name for every pin.
    pin_parts = []
    for slug, pin in pins.items():
        x, y = pin["x"], pin["y"]
        pin_parts.append(f'<circle cx="{x}" cy="{y}" r="1" fill="#e74c3c" stroke="#7a1f1f" stroke-width="0.2"/>')
        # paint-order="stroke" draws the white outline BEHIND the text, so
        # labels stay readable on top of dark green land.
        pin_parts.append(
            f'<text x="{x}" y="{y - 1.5}" font-size="1.6" text-anchor="middle" '
            f'fill="#111" stroke="white" stroke-width="0.25" paint-order="stroke">{pin["label"]}</text>'
        )

    return f'''<svg viewBox="0 0 100 100" width="1400" height="1400" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
    {body}
    {"".join(gridlines)}
    {"".join(pin_parts)}
</svg>'''


# --------------------------------------------------------------
# Run it: load pins, build the grid, write both SVGs.
# --------------------------------------------------------------
pins = load_pins()
cells = build_grid(pins)

with open(OUT_DIR / "kanto.svg", "w") as f:
    f.write(build_base_svg(cells))
print(f"wrote {OUT_DIR / 'kanto.svg'}")

with open(OUT_DIR / "kanto_calibration.svg", "w") as f:
    f.write(build_calibration_svg(cells, pins))
print(f"wrote {OUT_DIR / 'kanto_calibration.svg'}")
