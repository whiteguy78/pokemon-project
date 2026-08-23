"""
Map art helpers -- shared toolbox, not a script you run on its own.

Turns the reference map images in "images for claude/" into clean pixel-art
SVGs (a grid of <rect> cells -- "nothing fancy, just squares and colors"
per spec). Imported by prep/build_habitats.py and used to generate the
region maps in app/static/maps/.

The basic idea for all of it: chop the image into a coarse grid, pick one
colour per grid square, then draw one little rectangle per square. That's
what turns a photo into pixel art.

Two ways of picking that one colour, depending on the source image:

  - mode-color downsample: for the flat-color schematic maps (Johto, Hoenn,
    Sinnoh, Unova, Kalos). Takes the MOST COMMON color in each grid cell
    (not the average) so edges stay crisp instead of blurring into muddy
    intermediate colors.

  - averaged downsample + palette snap: for the photographic/illustrated
    maps (Paldea, Alola, Galar). Averages each cell (so it behaves like a
    real pixelation filter) then snaps to the nearest color in a curated
    palette so the result reads as clean pixel art instead of a blurry photo.
"""
import numpy as np
from PIL import Image
from collections import Counter


def load_rgb(path):
    """Open an image file as a plain grid of red/green/blue numbers."""
    # convert("RGB") throws away transparency and any palette weirdness so
    # everything downstream can assume 3 numbers per pixel.
    return np.array(Image.open(path).convert("RGB"))


def mode_downsample(img_arr, cols, rows):
    """Grid of `cols` x `rows` cells; each cell = its most common color."""
    h, w, _ = img_arr.shape
    cell_w = w / cols
    cell_h = h / rows
    grid = np.zeros((rows, cols, 3), dtype=np.uint8)
    for r in range(rows):
        # Which slice of the original image does this grid row cover?
        # The max(...) guards against a cell coming out zero pixels tall
        # when the image is small relative to the grid.
        y0, y1 = int(r * cell_h), max(int((r + 1) * cell_h), int(r * cell_h) + 1)
        for c in range(cols):
            x0, x1 = int(c * cell_w), max(int((c + 1) * cell_w), int(c * cell_w) + 1)
            # Grab that block of pixels and flatten it to a plain list of
            # colours, then take whichever colour appears most often.
            block = img_arr[y0:y1, x0:x1].reshape(-1, 3)
            colors, counts = np.unique(block, axis=0, return_counts=True)
            grid[r, c] = colors[np.argmax(counts)]
    return grid


def avg_downsample(img_arr, cols, rows):
    """Grid of `cols` x `rows` cells; each cell = its average color."""
    # Same as above, but averaging instead of voting. Good for photos,
    # bad for diagrams (it invents in-between colours along every edge).
    h, w, _ = img_arr.shape
    cell_w = w / cols
    cell_h = h / rows
    grid = np.zeros((rows, cols, 3), dtype=np.uint8)
    for r in range(rows):
        y0, y1 = int(r * cell_h), max(int((r + 1) * cell_h), int(r * cell_h) + 1)
        for c in range(cols):
            x0, x1 = int(c * cell_w), max(int((c + 1) * cell_w), int(c * cell_w) + 1)
            block = img_arr[y0:y1, x0:x1].reshape(-1, 3).astype(np.float32)
            grid[r, c] = block.mean(axis=0).astype(np.uint8)
    return grid


def snap_to_palette(grid, palette):
    """palette: list of (r,g,b). Replace every cell with its nearest palette color."""
    # "Nearest" here means nearest in RGB space -- treat each colour as a
    # point in 3D and take the closest one. Doing it with numpy in one go
    # rather than looping is much faster.
    pal = np.array(palette, dtype=np.float32)
    rows, cols, _ = grid.shape
    out = np.zeros_like(grid)
    flat = grid.reshape(-1, 3).astype(np.float32)
    # Distance from every cell to every palette colour, all at once.
    dists = ((flat[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
    nearest = pal[np.argmin(dists, axis=1)].astype(np.uint8)
    return nearest.reshape(rows, cols, 3)


def find_marker_blobs(img_arr, target_rgb, tolerance=30, min_size=6):
    """Find contiguous blobs of a marker color (e.g. pure red city squares).
    Returns list of (cx, cy, w, h) in ORIGINAL pixel coords via simple
    flood-fill connected components (no scipy available)."""
    # Used to spot the little coloured squares that mark cities on the
    # schematic maps, so they can be redrawn bigger and clearer.
    #
    # "Flood fill" = start on a matching pixel, then keep spreading to
    # matching neighbours until you can't any more. Everything you touched
    # is one blob. Repeat until every matching pixel has been visited.
    h, w, _ = img_arr.shape
    target = np.array(target_rgb)
    # Which pixels are close enough to the target colour to count?
    mask = (np.abs(img_arr.astype(int) - target).sum(axis=2) < tolerance)
    visited = np.zeros_like(mask, dtype=bool)
    blobs = []
    ys, xs = np.where(mask)
    coords = set(zip(ys.tolist(), xs.tolist()))
    for y, x in zip(ys.tolist(), xs.tolist()):
        if visited[y, x]:
            continue
        # BFS
        stack = [(y, x)]
        visited[y, x] = True
        pixels = []
        while stack:
            cy, cx = stack.pop()
            pixels.append((cy, cx))
            # look at the four neighbours: down, up, right, left
            for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not visited[ny, nx]:
                    visited[ny, nx] = True
                    stack.append((ny, nx))
        # Ignore specks -- they're usually anti-aliasing, not real markers.
        if len(pixels) >= min_size:
            pys = [p[0] for p in pixels]
            pxs = [p[1] for p in pixels]
            cy = sum(pys) / len(pys)  # centre of the blob
            cx = sum(pxs) / len(pxs)
            blobs.append((cx, cy, max(pxs) - min(pxs) + 1, max(pys) - min(pys) + 1))
    return blobs


def grid_to_svg(grid, cell_px=4, extra_rects=None):
    """grid: rows x cols x 3 uint8 array. Emits an SVG string, one <rect>
    per cell, viewBox sized to cols*cell_px x rows*cell_px so it stays
    crisp at any display size. extra_rects: list of (x,y,w,h,color) in the
    same cell-coordinate space, drawn on top (e.g. enlarged city markers)."""
    # This is the bit that actually writes the picture: an SVG is just
    # text, so we build up a list of "<rect .../>" strings and join them.
    # shape-rendering="crispEdges" stops the browser smoothing the pixels.
    rows, cols, _ = grid.shape
    vb_w, vb_h = cols * cell_px, rows * cell_px
    parts = [f'<svg viewBox="0 0 {vb_w} {vb_h}" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">']
    # merge consecutive same-color cells in a row into wider rects to keep the file smaller
    # (a row of 30 identical blue cells becomes one wide rect instead of 30)
    for r in range(rows):
        c = 0
        while c < cols:
            color = tuple(int(v) for v in grid[r, c])
            start = c
            # walk right for as long as the colour stays the same
            while c < cols and tuple(int(v) for v in grid[r, c]) == color:
                c += 1
            x = start * cell_px
            y = r * cell_px
            w = (c - start) * cell_px
            # NOTE: the int() casts above matter. Leave numpy's own number
            # type in here and it prints as "np.uint8(86)" inside the fill
            # colour, which silently renders every map solid black.
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{cell_px}" fill="rgb{color}"/>')
    if extra_rects:
        for (x, y, w, h, color) in extra_rects:
            parts.append(f'<rect x="{x*cell_px:.1f}" y="{y*cell_px:.1f}" width="{w*cell_px:.1f}" height="{h*cell_px:.1f}" fill="{color}" stroke="#000" stroke-width="0.4"/>')
    parts.append('</svg>')
    return "\n".join(parts)
