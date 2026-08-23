"""
STEP 1 of the data pipeline: download the whole of PokeAPI to disk.

This is a big, dumb, patient script. It asks PokeAPI "what kinds of things
do you have?", then for every kind (pokemon, moves, abilities, berries,
locations...) it downloads every single record and saves it as a JSON file
under data/raw/.

Why download it all instead of calling the API live?
  - The app then works offline and instantly, with no rate limits.
  - PokeAPI is a free service; hammering it on every page load is rude.
  - The data barely ever changes.

It's safe to stop this halfway through and run it again: anything already
saved gets skipped, so it picks up where it left off.

Run:  python3 prep/pokeapi_rip.py
Warning: this downloads a LOT (hundreds of MB) and takes a while.

Order of the pipeline:
  1. prep/pokeapi_rip.py       <-- you are here (download raw JSON)
  2. prep/build_pokedex_db.py  (turn that JSON into data/pokemon.db)
  3. prep/sprite_rip.py        (download the sprite images)
  4. prep/build_area_regions.py + the map/pin scripts (map data)
"""
import json
import sqlite3
import time
from pathlib import Path

import requests


# ============================================================
# CONFIG
# ============================================================

BASE_URL = "https://pokeapi.co/api/v2"

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = DATA_DIR / "pokemon.db"

# Tiny pause between requests so we're not spamming a free API.
REQUEST_DELAY = 0.05

# Number of times to retry a failed request
MAX_RETRIES = 5

# HTTP errors worth retrying.
# 429 = "you're going too fast", 5xx = "the server is having a bad day".
# Both usually fix themselves if you just wait a moment and ask again.
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


# ============================================================
# SET UP DIRECTORIES
# ============================================================

# parents=True: make any missing folders above this one too.
# exist_ok=True: don't complain if it's already there.
DATA_DIR.mkdir(parents=True, exist_ok=True)
RAW_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# API REQUEST FUNCTION
# ============================================================

def get_json(url):
    """
    Fetch one URL and return the parsed JSON.

    Doing this by hand (rather than a bare requests.get) because over tens
    of thousands of requests, a few WILL fail for boring reasons. So: try
    up to MAX_RETRIES times, waiting longer between each attempt
    (1s, 2s, 4s, 8s... -- that's what the 2 ** attempt is doing). Known as
    exponential backoff.
    """

    for attempt in range(MAX_RETRIES):

        try:

            response = requests.get(
                url,
                timeout=30
            )

            # ------------------------------------------------
            # Successful request
            # ------------------------------------------------

            # Throws an exception if the status code was an error one,
            # which drops us into the except blocks below.
            response.raise_for_status()

            # Be polite to PokeAPI
            time.sleep(REQUEST_DELAY)

            return response.json()

        except requests.exceptions.HTTPError as error:

            status_code = response.status_code

            # Retry only temporary/server-side errors
            if status_code in RETRY_STATUS_CODES:

                wait_time = 2 ** attempt

                print(
                    f"    HTTP {status_code} for {url}"
                )

                if attempt < MAX_RETRIES - 1:

                    print(
                        f"    Retrying in {wait_time} seconds..."
                    )

                    time.sleep(wait_time)

                else:

                    print(
                        f"    Failed after {MAX_RETRIES} attempts."
                    )

            else:

                # Don't retry permanent HTTP errors.
                # A 404 means it genuinely isn't there -- asking again
                # ten more times won't change that.
                raise error

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout
        ) as error:

            # Network hiccup rather than a server answer. Same deal:
            # wait and try again.
            wait_time = 2 ** attempt

            print(
                f"    Connection/timeout error for {url}"
            )

            if attempt < MAX_RETRIES - 1:

                print(
                    f"    Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

            else:

                print(
                    f"    Failed after {MAX_RETRIES} attempts."
                )

                raise error

    # Ran out of retries without ever returning.
    raise Exception(f"Unable to download: {url}")


# ============================================================
# FAILED DOWNLOAD LOG
# ============================================================

# Rather than crashing on a bad record, we write it to this file and carry
# on. Then you can look at the list afterwards and decide if it matters.
FAILED_LOG = RAW_DIR / "_failed_downloads.txt"


def log_failed_download(resource, url, error):

    # "a" means append -- add to the end of the file rather than
    # overwriting what's already there.
    with open(
        FAILED_LOG,
        "a",
        encoding="utf-8"
    ) as file:

        file.write(
            f"{resource}\t{url}\t{error}\n"
        )


# ============================================================
# DISCOVER ALL POKEAPI RESOURCES
# ============================================================

print("=" * 60)
print("DISCOVERING POKEAPI RESOURCES")
print("=" * 60)

# We don't hardcode a list of what to download. We ask the API's front
# page, and it tells us every category it has. If PokeAPI adds a new one
# later, this picks it up for free.
api_root = get_json(BASE_URL)

# PokeAPI's root response is a dictionary like:
#
# {
#     "ability": "https://pokeapi.co/api/v2/ability/",
#     "berry": "https://pokeapi.co/api/v2/berry/",
#     "pokemon": "https://pokeapi.co/api/v2/pokemon/",
#     ...
# }

resources = api_root

print(f"\nFound {len(resources)} API resources:\n")

for resource, url in resources.items():

    print(f"  {resource}")


# ============================================================
# SAVE API ROOT / MANIFEST
# ============================================================

# Keep a copy of that index, so later you can see exactly what the API
# looked like on the day you downloaded everything.
manifest_file = RAW_DIR / "_api_manifest.json"

with open(
    manifest_file,
    "w",
    encoding="utf-8"
) as file:

    json.dump(
        api_root,
        file,
        indent=2,          # pretty-print it so it's readable
        ensure_ascii=False  # keep accented characters as-is
    )

print(f"\nSaved API manifest:")
print(manifest_file)


# ============================================================
# CRAWL EVERY RESOURCE
# ============================================================

print()
print("=" * 60)
print("DOWNLOADING POKEAPI")
print("=" * 60)


for resource, resource_url in resources.items():

    print()
    print("-" * 60)
    print(f"RESOURCE: {resource}")
    print("-" * 60)

    # --------------------------------------------------------
    # CREATE DIRECTORY FOR THIS RESOURCE
    # --------------------------------------------------------

    # One folder per category: data/raw/pokemon/, data/raw/move/, etc.
    resource_dir = RAW_DIR / resource

    resource_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    # --------------------------------------------------------
    # GET RESOURCE INDEX
    # --------------------------------------------------------

    # First get the LIST of things in this category. The API hands it over
    # in pages of 20, with a "next" link to the following page, so we keep
    # following "next" until it comes back empty.

    url = resource_url

    resource_list = []

    try:

        while url:

            print(f"Reading index: {url}")

            data = get_json(url)

            resource_list.extend(
                data["results"]
            )

            url = data["next"]  # None on the last page, which ends the loop

    except Exception as error:

        # Couldn't even get the list for this category. Note it and move
        # on to the next one rather than giving up entirely.
        print()
        print(
            f"FAILED TO READ INDEX FOR: {resource}"
        )

        print(error)

        log_failed_download(
            resource,
            resource_url,
            f"INDEX ERROR: {error}"
        )

        # Move on to the next API resource
        continue

    print(
        f"Found {len(resource_list)} records"
    )

    # --------------------------------------------------------
    # DOWNLOAD INDIVIDUAL RECORDS
    # --------------------------------------------------------

    # Counters, purely so the summary at the end is useful.
    downloaded = 0
    skipped = 0
    failed = 0

    for item in resource_list:

        item_url = item["url"]

        # Pull the id number off the end of the URL, to name the file.
        #
        # Example:
        #
        # https://pokeapi.co/api/v2/pokemon/35/
        #
        # becomes:
        #
        # 35

        item_id = (
            item_url
            .rstrip("/")      # drop the trailing slash
            .split("/")[-1]   # take the last chunk
        )

        output_file = (
            resource_dir /
            f"{item_id}.json"
        )

        # ----------------------------------------------------
        # DON'T DOWNLOAD SOMETHING WE ALREADY HAVE
        # ----------------------------------------------------

        # This is what makes the script resumable.
        if output_file.exists():

            skipped += 1
            continue

        print(
            f"  Downloading {item_id}"
        )

        # ----------------------------------------------------
        # DOWNLOAD RECORD
        # ----------------------------------------------------

        try:

            item_data = get_json(
                item_url
            )

        except Exception as error:

            failed += 1

            print(
                f"  FAILED: {item_id}"
            )

            print(
                f"  {error}"
            )

            log_failed_download(
                resource,
                item_url,
                error
            )

            # IMPORTANT:
            #
            # Don't kill the entire crawl because
            # one individual record failed.
            #
            continue

        # ----------------------------------------------------
        # SAVE RECORD
        # ----------------------------------------------------

        with open(
            output_file,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                item_data,
                file,
                indent=2,
                ensure_ascii=False
            )

        downloaded += 1

    # --------------------------------------------------------
    # RESOURCE SUMMARY
    # --------------------------------------------------------

    print()
    print(
        f"  Found:      {len(resource_list)}"
    )

    print(
        f"  Downloaded: {downloaded}"
    )

    print(
        f"  Cached:     {skipped}"
    )

    print(
        f"  Failed:     {failed}"
    )


# ============================================================
# CREATE EMPTY SQLITE DATABASE
# ============================================================

# Just a stub database with a note about where the data came from.
# The real tables get built by prep/build_pokedex_db.py, which is the
# next step.

print()
print("=" * 60)
print("CREATING SQLITE DATABASE")
print("=" * 60)

conn = sqlite3.connect(
    DB_PATH
)

cursor = conn.cursor()


cursor.execute("""
CREATE TABLE IF NOT EXISTS database_info (
    key TEXT PRIMARY KEY,
    value TEXT
)
""")


cursor.execute("""
INSERT OR REPLACE INTO database_info
(key, value)
VALUES (?, ?)
""", (
    "source",
    "PokeAPI"
))


cursor.execute("""
INSERT OR REPLACE INTO database_info
(key, value)
VALUES (?, ?)
""", (
    "raw_data_directory",
    str(RAW_DIR)
))


cursor.execute("""
INSERT OR REPLACE INTO database_info
(key, value)
VALUES (?, ?)
""", (
    "api_manifest",
    str(manifest_file)
))


# commit() = actually save the changes. Without it they're thrown away.
conn.commit()
conn.close()


# ============================================================
# DONE
# ============================================================

print()
print("=" * 60)
print("POKEDEX DOWNLOAD COMPLETE")
print("=" * 60)

print()
print(f"Raw data: {RAW_DIR}")
print(f"Database: {DB_PATH}")

if FAILED_LOG.exists():

    print(
        f"Failed downloads were logged to:"
    )

    print(
        FAILED_LOG
    )

print()
