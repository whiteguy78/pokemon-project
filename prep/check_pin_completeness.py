"""
A checking tool, not a build step. Nothing depends on it.

Sweeps all 7 non-Kanto, non-Paldea region pin files
(data/maps/{region}_pins.json) and prints any location-area slug PokeAPI's
cached bulk data knows about that has no pin yet -- i.e. places that will
show up in the app's location list with no dot on the map.

Exits with code 1 if any region has gaps, 0 otherwise, so it can be
dropped into a CI check later if you ever want that.

Deliberately doesn't import app/main.py (which opens a database connection
the moment it's imported) or build_region_pins.py -- it just repeats the
two tiny lookup helpers so this stays a standalone check with no side
effects. A bit of duplication is the right trade here.

Run: python3 prep/check_pin_completeness.py
"""
import json
import sys
from pathlib import Path

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
MAPS_DATA_DIR = PROJECT_DIR / "data" / "maps"

REGION_IDS = {
    "johto": 2, "hoenn": 3, "sinnoh": 4, "unova": 5,
    "kalos": 6, "alola": 7, "galar": 8,
}


def load_region_location_ids(region):
    """Every location id belonging to this region."""
    with open(RAW_DIR / "region" / f"{REGION_IDS[region]}.json") as f:
        data = json.load(f)
    return [loc["url"].rstrip("/").split("/")[-1] for loc in data.get("locations", [])]


def load_location_areas(location_id):
    """Every area slug inside one location."""
    with open(RAW_DIR / "location" / f"{location_id}.json") as f:
        data = json.load(f)
    return [a["name"] for a in data.get("areas", [])]


def main():
    any_missing = False

    for region in REGION_IDS:
        # What we HAVE pinned.
        with open(MAPS_DATA_DIR / f"{region}_pins.json") as f:
            pins = json.load(f)

        # What EXISTS according to PokeAPI.
        all_areas = set()
        for loc_id in load_region_location_ids(region):
            all_areas.update(load_location_areas(loc_id))

        # The gap between the two. Sets make this a one-liner: "everything
        # that exists, minus everything we've pinned".
        missing = sorted(all_areas - set(pins.keys()))
        print(f"{region}: {len(pins)}/{len(all_areas)} area slugs pinned, {len(missing)} missing")
        if missing:
            any_missing = True
            for slug in missing:
                print(f"  missing: {slug}")

    # Exit code 0 = all good, 1 = something's missing. This is the normal
    # convention for command line tools, and it's what lets other tools
    # (a script, CI) tell whether this passed.
    sys.exit(1 if any_missing else 0)


if __name__ == "__main__":
    main()
