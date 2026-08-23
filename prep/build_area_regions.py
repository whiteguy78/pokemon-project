"""
STEP 4 of the data pipeline: work out which REGION every location is in.

Builds data/maps/location_area_regions.json -- a flat
{location_area_slug: region_name} index covering every region in the
offline PokeAPI bulk cache. It looks like:

    {"viridian-forest-area": "kanto", "route-29-area": "johto", ...}

app/main.py needs this because a game's GENERATION doesn't tell you which
REGION its locations are in. The remakes and multi-region games break
that assumption badly:
  - FireRed/LeafGreen are generation 3, but set in Kanto (not Hoenn)
  - HeartGold/SoulSilver are generation 4, but set in Johto + Kanto
  - Omega Ruby/Alpha Sapphire are generation 6, but set in Hoenn
  - Gold/Silver/Crystal reach Kanto in the postgame
Without this index those games render the wrong region's map entirely,
and none of their locations can resolve a pin.

Verified safe: no location-area slug is claimed by more than one region,
so the mapping is unambiguous.

Run: python3 prep/build_area_regions.py
"""
import json
import os
from pathlib import Path

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_DIR / "data" / "raw"
OUT_PATH = PROJECT_DIR / "data" / "maps" / "location_area_regions.json"


def main():
    area_to_region = {}
    collisions = []  # any slug two regions both claim -- should stay empty

    # The data is nested three levels deep, so this is three loops:
    #   region (kanto) -> location (viridian-forest) -> area (…-area)
    # We only care about the innermost name, since that's what PokeAPI's
    # encounter data actually refers to.
    for filename in sorted(os.listdir(RAW_DIR / "region")):
        with open(RAW_DIR / "region" / filename) as f:
            region = json.load(f)

        for loc_ref in region.get("locations", []):
            # The region file only gives us links to its locations, so
            # pull the id off the end of the URL and open that file.
            loc_id = loc_ref["url"].rstrip("/").split("/")[-1]
            loc_path = RAW_DIR / "location" / f"{loc_id}.json"
            if not os.path.exists(loc_path):
                continue  # not in our cache; nothing we can do
            with open(loc_path) as f:
                location = json.load(f)

            for area in location.get("areas", []):
                slug = area["name"]
                # If some other region already claimed this slug, that
                # would make the whole index unreliable -- note it so the
                # warning at the bottom can shout about it.
                if slug in area_to_region and area_to_region[slug] != region["name"]:
                    collisions.append((slug, area_to_region[slug], region["name"]))
                area_to_region[slug] = region["name"]

    # sort_keys=True keeps the output file in a stable order, so re-running
    # this doesn't produce a giant meaningless diff.
    with open(OUT_PATH, "w") as f:
        json.dump(area_to_region, f, indent=2, sort_keys=True)

    # Count how many areas ended up in each region, purely as a sanity
    # check you can eyeball.
    by_region = {}
    for slug_region in area_to_region.values():
        by_region[slug_region] = by_region.get(slug_region, 0) + 1

    print(f"wrote {OUT_PATH}: {len(area_to_region)} location-areas")
    for name, count in sorted(by_region.items()):
        print(f"  {name:10s} {count}")
    if collisions:
        print(f"WARNING: {len(collisions)} slug(s) claimed by multiple regions: {collisions[:5]}")


# Only run main() if this file was launched directly, not if something
# imported it.
if __name__ == "__main__":
    main()
