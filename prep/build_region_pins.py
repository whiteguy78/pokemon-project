"""
Places the map dots for the 8 non-Kanto regions.

The problem this solves: you can hand-place a pin for "Blackthorn City"
easily enough, but PokeAPI's encounter data doesn't talk about cities. It
talks about location-AREAS -- "blackthorn-city-area", "route-45-area",
"mt-moon-b1f". There are thousands of them, and hand-placing every one
would be miserable.

So the work is split in two:
  - YOU hand-write one pin per named place in
    data/maps/location_pins/{region}.json. That's the actual content work.
  - THIS SCRIPT mechanically expands that into one pin per location-area
    in data/maps/{region}_pins.json (same {x, y, label} schema as
    kanto_pins.json), by looking up which areas belong to which location
    in the offline PokeAPI bulk cache (data/raw/region, data/raw/location).
    Every area just inherits its parent location's coordinates.

It also writes app/static/maps/{region}_calibration.svg -- the region's
existing map art with a numbered grid and labelled dots drawn on top, so
you can see whether your pins landed anywhere sensible.

Unlike build_kanto_map.py, this script never generates landmass art --
app/static/maps/{region}.svg is fixed reference art built once from real
map images (see prep/pixelate_map.py) and is only ever read here, never
written.

Run: python3 prep/build_region_pins.py <region>|all
"""
import json
import os
import re
import sys
from pathlib import Path

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
MAPS_DATA_DIR = PROJECT_DIR / "data" / "maps"
MAPS_ART_DIR = PROJECT_DIR / "app" / "static" / "maps"

REGION_IDS = {  # PokeAPI region ids, from data/raw/region/{id}.json
    "johto": 2, "hoenn": 3, "sinnoh": 4, "unova": 5,
    "kalos": 6, "alola": 7, "galar": 8,
}  # paldea deliberately excluded -- 0 location-area data upstream

# Area slugs end in things like "-1f" or "-north". Left alone, the labels
# would read "Mt Moon 1F" as "Mt Moon 1f" -- this just tidies the suffix.
SUFFIX_SHORTHAND = {
    "1f": "1F", "2f": "2F", "3f": "3F", "4f": "4F", "5f": "5F",
    "b1f": "B1", "b2f": "B2", "b3f": "B3", "b4f": "B4",
    "north": "(N)", "south": "(S)", "east": "(E)", "west": "(W)",
}

# area_slug -> label, for the handful of slugs that don't clean up well
# via the mechanical suffix-stripping below (e.g. Alola's double-hyphen
# compound slugs).
MANUAL_LABEL_OVERRIDES = {}

# area_slug -> {"x":, "y":}, for the rare case where a single location's
# child areas are meant to scatter across the map instead of sharing one
# point -- e.g. Hoenn's "mirage-spot-*" locations, whose area slugs are
# literally named by relative position ("north-of-fortree",
# "west-of-rustboro"). Takes precedence over the inherited location x/y.
AREA_PIN_OVERRIDES = {
    # Hoenn ORAS DexNav mirage spots -- each area slug names its own
    # position relative to a real map anchor, so place it there directly
    # instead of clustering all 32 at one point.
    "mirage-spot-cave-south-of-pacifidlog": {"x": 62, "y": 74},
    "mirage-spot-cave-north-of-route-132": {"x": 48, "y": 58},
    "mirage-spot-cave-north-of-fallarbor": {"x": 15, "y": 7},
    "mirage-spot-cave-north-of-fortree": {"x": 45, "y": 7},
    "mirage-spot-cave-south-east-of-route-129": {"x": 82, "y": 68},
    "mirage-spot-cave-south-of-route-107": {"x": 16, "y": 88},
    "mirage-spot-cave-north-of-route-124": {"x": 76, "y": 26},
    "mirage-spot-cave-west-of-rustburo": {"x": 1, "y": 43},

    "mirage-spot-forest-north-of-lilycove": {"x": 66, "y": 22},
    "mirage-spot-forest-south-of-route-132": {"x": 48, "y": 72},
    "mirage-spot-forest-east-of-mossdeep": {"x": 94, "y": 40},
    "mirage-spot-forest-south-of-route-109": {"x": 26, "y": 80},
    "mirage-spot-forest-north-of-route-124": {"x": 74, "y": 25},
    "mirage-spot-forest-west-of-route-114": {"x": 16, "y": 12},
    "mirage-spot-forest-west-of-route-105": {"x": 3, "y": 68},
    "mirage-spot-forest-south-of-route-111": {"x": 28, "y": 41},

    "mirage-spot-island-west-of-dewford-town": {"x": 6, "y": 86},
    "mirage-spot-island-west-of-route-104": {"x": 2, "y": 52},
    "mirage-spot-island-route-114": {"x": 24, "y": 14},
    "mirage-spot-island-route-124": {"x": 78, "y": 36},
    "mirage-spot-island-route-132": {"x": 50, "y": 64},
    "mirage-spot-island-south-of-route-134": {"x": 36, "y": 73},
    "mirage-spot-island-south-of-pacifidlog": {"x": 60, "y": 72},
    "mirage-spot-island-east-of-shoal-cave": {"x": 88, "y": 32},

    "mirage-spot-mountain-east-of-mossdeep": {"x": 93, "y": 44},
    "mirage-spot-mountain-north-of-mossdeep": {"x": 87, "y": 30},
    "mirage-spot-mountain-south-east-of-route-129": {"x": 84, "y": 70},
    "mirage-spot-mountain-north-of-lilycove": {"x": 68, "y": 20},
    "mirage-spot-mountain-west-of-route-104": {"x": 2, "y": 56},
    "mirage-spot-mountain-south-of-route-129": {"x": 75, "y": 68},
    "mirage-spot-mountain-south-of-route-131": {"x": 78, "y": 68},
    "mirage-spot-mountain-north-east-of-route-125": {"x": 92, "y": 42},
}


def load_region_locations(region):
    # -> {location_slug: location_id}
    # e.g. {"blackthorn-city": "123", "route-45": "124", ...}
    region_id = REGION_IDS[region]
    with open(RAW_DIR / "region" / f"{region_id}.json") as f:
        data = json.load(f)
    locations = {}
    for loc in data.get("locations", []):
        # The region file gives links, not ids, so take the last chunk
        # of the URL.
        loc_id = loc["url"].rstrip("/").split("/")[-1]
        locations[loc["name"]] = loc_id
    return locations


def load_location_areas(location_id):
    # -> [area_slug, ...]
    # One location can have several areas: mt-moon becomes mt-moon-1f,
    # mt-moon-b1f, mt-moon-b2f and so on.
    path = RAW_DIR / "location" / f"{location_id}.json"
    if not os.path.exists(path):
        return []
    with open(path) as f:
        data = json.load(f)
    return [a["name"] for a in data.get("areas", [])]


def derive_area_label(location_slug, area_slug, base_label):
    """Turn an area slug into a readable label, e.g. "Mt Moon B1"."""
    if area_slug in MANUAL_LABEL_OVERRIDES:
        return MANUAL_LABEL_OVERRIDES[area_slug]

    # Chop the parent's name off the front and see what's left.
    # "mt-moon-b1f" minus "mt-moon" leaves "b1f".
    suffix = area_slug[len(location_slug):].lstrip("-")
    if suffix in ("", "area"):
        return base_label  # nothing meaningful left; use the plain name

    parts = suffix.split("-")
    display = " ".join(SUFFIX_SHORTHAND.get(p, p.title()) for p in parts)
    return f"{base_label} {display}"


def build_area_pins(region, location_pins):
    """Expand your hand-written location pins into one pin per area."""
    locations = load_region_locations(region)
    area_pins = {}
    unresolved = []  # names you wrote that PokeAPI doesn't recognise

    for location_slug, pin in location_pins.items():
        loc_id = locations.get(location_slug)
        if loc_id is None:
            # Usually a typo in the hand-written file, so it gets reported
            # rather than silently dropped.
            unresolved.append(location_slug)
            continue
        for area_slug in load_location_areas(loc_id):
            # Normally the area just sits wherever its parent location
            # does, unless it's one of the special cases listed above.
            override = AREA_PIN_OVERRIDES.get(area_slug, {})
            area_pins[area_slug] = {
                "x": override.get("x", pin["x"]),
                "y": override.get("y", pin["y"]),
                "label": derive_area_label(location_slug, area_slug, pin["label"]),
            }

    if unresolved:
        print(f"  WARNING: {len(unresolved)} location slug(s) not found in region data: {unresolved}")

    return area_pins


def check_completeness(region, area_pins):
    """Which areas in this region still have no pin? (set subtraction)"""
    locations = load_region_locations(region)
    all_areas = set()
    for loc_id in locations.values():
        all_areas.update(load_location_areas(loc_id))
    return sorted(all_areas - set(area_pins.keys()))


# Two little patterns for pulling bits out of an existing SVG file.
# The first grabs the two numbers out of viewBox="0 0 520 340"; the second
# grabs everything between the opening <svg ...> tag and the closing one.
# (re.DOTALL lets "." match newlines, since the art spans many lines.)
VIEWBOX_RE = re.compile(r'viewBox="0 0 (\d+) (\d+)"')
BODY_RE = re.compile(r">(.*)</svg>", re.DOTALL)


def extract_svg_body_and_viewbox(svg_path):
    """Read the existing map art so we can redraw it with a grid on top."""
    with open(svg_path) as f:
        content = f.read()
    width, height = (int(v) for v in VIEWBOX_RE.search(content).groups())
    body = BODY_RE.search(content).group(1)
    return body, width, height


def build_calibration_svg(body, width, height, location_pins):
    """The region's real map art + a numbered grid + labelled dots on top."""
    # Kanto's calibration constants (stroke 0.15, dot r=1, font 1.6-2) were
    # tuned for a 100x100 viewBox -- scale them to whatever this region's
    # native units are so they stay visible/legible at any size.
    # Everything below multiplies by `unit` for exactly that reason.
    unit = max(width, height) / 100

    parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">']
    parts.append(body)  # the existing map art, untouched

    # Gridlines every 10%, numbered, so you can read coordinates off it.
    for i in range(0, 101, 10):
        gx, gy = i / 100 * width, i / 100 * height
        parts.append(f'<line x1="{gx}" y1="0" x2="{gx}" y2="{height}" stroke="black" stroke-width="{0.15 * unit}" opacity="0.35"/>')
        parts.append(f'<line x1="0" y1="{gy}" x2="{width}" y2="{gy}" stroke="black" stroke-width="{0.15 * unit}" opacity="0.35"/>')
        parts.append(f'<text x="{gx + 0.5 * unit}" y="{2 * unit}" font-size="{2 * unit}" fill="black">{i}</text>')
        parts.append(f'<text x="{0.5 * unit}" y="{gy + 2 * unit}" font-size="{2 * unit}" fill="black">{i}</text>')

    # One dot per authored LOCATION (not per expanded area) so co-located
    # sub-areas (e.g. a route split into -main/-lake/-lakeside) don't stack
    # duplicate dots on top of each other.
    for pin in location_pins.values():
        cx, cy = pin["x"] / 100 * width, pin["y"] / 100 * height
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{unit}" fill="#e74c3c" stroke="#7a1f1f" stroke-width="{0.2 * unit}"/>')
        parts.append(
            f'<text x="{cx}" y="{cy - 1.5 * unit}" font-size="{1.6 * unit}" text-anchor="middle" '
            f'fill="#111" stroke="white" stroke-width="{0.25 * unit}" paint-order="stroke">{pin["label"]}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


def build_region(region):
    """Do the whole job for one region."""
    # 1. Read the hand-written location pins (the human input).
    location_pins_path = MAPS_DATA_DIR / "location_pins" / f"{region}.json"
    if not os.path.exists(location_pins_path):
        print(f"{region}: no {location_pins_path} yet, skipping")
        return

    with open(location_pins_path) as f:
        location_pins = json.load(f)

    # 2. Expand them into area-level pins, and see what's still missing.
    area_pins = build_area_pins(region, location_pins)
    missing = check_completeness(region, area_pins)

    # 3. Write the file the app actually reads.
    with open(MAPS_DATA_DIR / f"{region}_pins.json", "w") as f:
        json.dump(area_pins, f, indent=2, sort_keys=True)

    # 4. Write the visual check file.
    body, width, height = extract_svg_body_and_viewbox(MAPS_ART_DIR / f"{region}.svg")
    with open(MAPS_ART_DIR / f"{region}_calibration.svg", "w") as f:
        f.write(build_calibration_svg(body, width, height, location_pins))

    print(f"{region}: {len(location_pins)} locations -> {len(area_pins)} areas pinned, {len(missing)} missing")
    if missing:
        print(f"  missing: {missing}")


def main():
    # sys.argv is the list of words you typed. sys.argv[0] is the script
    # name itself, so sys.argv[1] is the first real argument.
    if len(sys.argv) != 2:
        print("Usage: python3 prep/build_region_pins.py <region>|all")
        sys.exit(1)

    regions = list(REGION_IDS) if sys.argv[1] == "all" else [sys.argv[1]]
    for region in regions:
        build_region(region)


if __name__ == "__main__":
    main()
