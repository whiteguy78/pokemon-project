"""
Draws the nine pixel-art habitat background scenes.

Every pokemon has a habitat (cave, forest, sea...), and the app puts a
little scene behind the sprite to match. This script draws those scenes.

Important: this is a ONE-OFF art generator, not part of the app's runtime.
It writes SVG files into prep/output/habitats/, and the finished SVGs were
then pasted into app/static/script.js as the habitat* functions. Re-run
this only if you want to change the artwork; then copy the new SVG text
back into script.js.

Style: small blocky grids (24 x 16 squares), same look as the region maps,
inspired by the PC-box thumbnail strips in "images for claude/habitats.png"
(forest bushes + sky, night city skyline, beach, water waves, snow
mountains, volcanic wasteland).

Run: python3 prep/build_habitats.py
"""
import json
from pathlib import Path

import numpy as np

# Both files live in prep/, and Python automatically puts a script's own
# folder on the import path, so this plain import just works.
from pixelate_map import grid_to_svg

OUT_DIR = Path(__file__).resolve().parent / "output" / "habitats"


# ---------------------------------------------------------------
# TINY DRAWING TOOLBOX
# A "grid" here is just a 2D array of squares, each holding an (r, g, b)
# colour. These helpers colour in different shapes of squares. Think of it
# as MS Paint with five tools.
# ---------------------------------------------------------------

def new_grid(w, h, bg):
    """A blank canvas, w x h squares, filled with one background colour."""
    g = np.zeros((h, w, 3), dtype=np.uint8)
    g[:] = bg
    return g


def fill_rows(grid, y0, y1, color):
    """Paint horizontal bands -- ground, sky, water, etc."""
    grid[y0:y1, :] = color


def set_px(grid, x, y, color):
    """Colour one single square. Ignores anything off the edge."""
    h, w, _ = grid.shape
    if 0 <= x < w and 0 <= y < h:
        grid[y, x] = color


def triangle(grid, cx, base_y, height, half_w, color):
    """A triangle standing on its base -- used for trees and mountains.

    Draws it one row at a time, narrowing as it goes up: at the bottom the
    row is `half_w` wide either side of the centre, at the top it's zero.
    """
    for row in range(height):
        y = base_y - row
        w_at_row = int(half_w * (1 - row / height))
        for x in range(cx - w_at_row, cx + w_at_row + 1):
            set_px(grid, x, y, color)


def speckle(grid, x0, x1, y0, y1, color, density, seed):
    """Scatter random dots -- stars, gravel, water droplets.

    `density` is the chance any given square gets coloured (0.15 = 15%).
    `seed` fixes the randomness, so re-running gives the identical picture
    instead of reshuffling every time.
    """
    rng = np.random.default_rng(seed)
    for y in range(y0, y1):
        for x in range(x0, x1):
            if rng.random() < density:
                set_px(grid, x, y, color)


def rect(grid, x0, y0, x1, y1, color):
    """A filled rectangle -- buildings, doors, tree trunks."""
    grid[y0:y1, x0:x1] = color


# ---------------------------------------------------------------
# THE NINE SCENES
# Each one is: start with a background, then stack shapes on top. They're
# built top-to-bottom the way you'd paint them, so read each block in
# order and you can picture the result.
# ---------------------------------------------------------------

W, H = 24, 16   # every scene is 24 squares wide, 16 tall
OUT = {}        # habitat name -> finished grid

# ---------------- CAVE ----------------
# Dark blue-purple, stalactites hanging from the ceiling, a few glinting
# water droplets, gravelly floor.
g = new_grid(W, H, (26, 24, 40))
fill_rows(g, 11, H, (20, 18, 32))          # darker floor
for cx in (3, 8, 13, 18, 21):
    triangle(g, cx, 4, 4, 1, (44, 40, 64))  # stalactites (pointing down-ish)
speckle(g, 0, W, 0, 11, (70, 110, 160), 0.02, 1)   # rare blue glints
speckle(g, 0, W, 11, H, (60, 56, 84), 0.15, 2)     # rubble on the floor
OUT['cave'] = g

# ---------------- FOREST ----------------
# Sky, then two staggered rows of pine trees, then grass.
g = new_grid(W, H, (150, 205, 225))
fill_rows(g, 10, H, (58, 110, 46))
for cx, ch in ((2, 8), (6, 9), (10, 8), (14, 9), (18, 8), (21, 9)):
    triangle(g, cx, 12, ch, 3, (34, 82, 30))    # back row, darker
for cx, ch in ((4, 6), (8, 7), (16, 6), (20, 7)):
    triangle(g, cx, 13, ch, 2, (46, 120, 40))   # front row, lighter
fill_rows(g, 14, H, (44, 96, 36))
OUT['forest'] = g

# ---------------- GRASSLAND ----------------
# Sky, two clouds, a green field in two shades, four flowers.
g = new_grid(W, H, (135, 206, 235))
fill_rows(g, 9, H, (140, 205, 100))
fill_rows(g, 12, H, (120, 190, 84))
rect(g, 5, 6, 8, 7, (255, 255, 255))    # cloud
rect(g, 15, 4, 19, 5, (255, 255, 255))  # cloud
for x, y, c in ((3, 11, (255, 210, 90)), (9, 13, (255, 140, 170)), (17, 12, (255, 210, 90)), (20, 14, (255, 140, 170))):
    set_px(g, x, y, c)
OUT['grassland'] = g

# ---------------- MOUNTAIN ----------------
# Three overlapping grey peaks, white snow caps on each, tan foreground.
g = new_grid(W, H, (150, 205, 232))
triangle(g, 6, 12, 9, 6, (120, 128, 140))
triangle(g, 17, 13, 8, 6, (104, 112, 126))
triangle(g, 12, 14, 11, 7, (140, 148, 160))
triangle(g, 6, 12, 3, 2, (255, 255, 255))   # snow caps: same centres,
triangle(g, 12, 14, 4, 2, (255, 255, 255))  # much shorter triangles
triangle(g, 17, 13, 3, 2, (255, 255, 255))
fill_rows(g, 14, H, (168, 176, 150))
OUT['mountain'] = g

# ---------------- RARE (treasure vault) ----------------
# A vault door with a gold dial, and coins scattered on the floor.
g = new_grid(W, H, (58, 42, 30))
fill_rows(g, 12, H, (40, 28, 20))
rect(g, 9, 3, 15, 12, (94, 74, 50))   # door frame
rect(g, 10, 4, 14, 11, (74, 56, 38))  # door
circ_cx, circ_cy = 12, 7
# A filled circle, drawn the manual way: colour any square whose distance
# from the centre is within the radius (dx^2 + dy^2 <= r^2).
for dy in range(-2, 3):
    for dx in range(-2, 3):
        if dx*dx + dy*dy <= 4:
            set_px(g, circ_cx+dx, circ_cy+dy, (212, 175, 55))
for x, y in ((3, 13), (5, 14), (19, 13), (20, 14), (7, 12), (17, 14)):
    set_px(g, x, y, (212, 175, 55))       # coin
    set_px(g, x+1, y, (235, 200, 80))     # its highlight
OUT['rare'] = g

# ---------------- ROUGH TERRAIN (volcanic wasteland) ----------------
# Purple sky, cracked brown ground, dark rock spikes, orange lava vents.
g = new_grid(W, H, (120, 70, 100))
fill_rows(g, 9, H, (150, 90, 60))
fill_rows(g, 12, H, (110, 62, 44))
triangle(g, 4, 9, 5, 1, (60, 34, 26))
triangle(g, 19, 9, 6, 1, (60, 34, 26))
speckle(g, 0, W, 9, H, (90, 48, 34), 0.15, 3)  # cracked/rubbly texture
for x, y in ((10, 3), (13, 5)):
    triangle(g, x, y+2, 3, 1, (230, 120, 40))  # lava spurts
OUT['rough-terrain'] = g

# ---------------- SEA ----------------
# Bands of blue getting lighter toward the bottom, with dashed white
# crests along the boundaries.
g = new_grid(W, H, (26, 88, 168))
for y, c in ((3, (40, 110, 190)), (7, (52, 130, 205)), (11, (70, 150, 215))):
    fill_rows(g, y, y+2, c)
for y in (2, 6, 10, 13):
    for x in range(0, W, 4):          # every 4th square, two wide
        set_px(g, x, y, (200, 230, 250))
        set_px(g, x+1, y, (200, 230, 250))
OUT['sea'] = g

# ---------------- URBAN (night skyline) ----------------
# Night sky with stars, six buildings of different heights, lit windows.
g = new_grid(W, H, (36, 30, 70))
fill_rows(g, 13, H, (24, 20, 46))
buildings = [(1, 6, 4), (5, 4, 5), (9, 7, 3), (12, 5, 4), (16, 8, 3), (19, 5, 4)]  # (x, height, width)
for x0, height, width in buildings:
    rect(g, x0, 13-height, x0+width, 13, (50, 44, 84))
    # Windows every other row and column, so they form a grid rather than
    # a solid yellow block.
    for yy in range(13-height+1, 13, 2):
        for xx in range(x0+1, x0+width, 2):
            set_px(g, xx, yy, (255, 224, 120))
speckle(g, 0, W, 0, 6, (255, 255, 255), 0.03, 4)  # stars
OUT['urban'] = g

# ---------------- WATERS EDGE (beach) ----------------
# Sea up top, shallow surf, sand below, two little palm trees.
g = new_grid(W, H, (235, 214, 165))
fill_rows(g, 0, 9, (58, 150, 210))
fill_rows(g, 9, 11, (110, 190, 225))
for y in (2, 5):
    for x in range(0, W, 5):
        set_px(g, x, y, (220, 240, 250))  # wave crests
fill_rows(g, 11, H, (222, 198, 145))
for x, y in ((4, 13), (18, 12)):
    rect(g, x, y, x+2, y+3, (150, 100, 60))     # trunk
    triangle(g, x+1, y-1, 3, 3, (60, 150, 70))  # leaves
OUT['waters-edge'] = g


# ---------------------------------------------------------------
# WRITE THEM OUT
# ---------------------------------------------------------------
OUT_DIR.mkdir(parents=True, exist_ok=True)

for name, grid in OUT.items():
    svg = grid_to_svg(grid, cell_px=5)
    print(f"{name}: {len(svg)} bytes")
    with open(OUT_DIR / f"habitat_{name}.svg", "w") as f:
        f.write(svg)

# Also dump the raw grids as JSON, in case you want to tweak the colours
# later without re-deriving the shapes.
with open(OUT_DIR / "habitat_grids.json", "w") as f:
    json.dump({k: v.tolist() for k, v in OUT.items()}, f)

print(f"\nwrote {len(OUT)} habitat SVGs to {OUT_DIR}")
print("To use them: copy the SVG text into the habitat* functions in app/static/script.js")
