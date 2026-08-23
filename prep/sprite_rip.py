"""
STEP 3 of the data pipeline: download the sprite images.

The JSON we downloaded in step 1 doesn't contain the actual pictures -- it
just contains LINKS to them. This script goes through every pokemon in the
database, reads those links out of its saved JSON file, and downloads the
images into data/sprites/.

Files come out named "{pokemon_id}_{sprite_name}.png", e.g.
"6_front_shiny.png". The web server (app/main.py) relies on exactly that
naming to find them later, so don't rename them.

We only keep the front-facing sprites. Back sprites are skipped -- the app
never shows one, so there's no point downloading ~1,300 extra images.

Run:  python3 prep/sprite_rip.py
Takes a while (roughly 3,000 small downloads) and is safe to re-run.
"""
import requests
import json
import sqlite3
import os
import pandas as pd
import time
from pathlib import Path

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
RAW_POKEMON_DIR = PROJECT_DIR / "data" / "raw" / "pokemon"
SPRITES_DIR = PROJECT_DIR / "data" / "sprites"
DB_PATH = PROJECT_DIR / "data" / "pokemon.db"


def download_sprites(pokemon_id):
    """Download every front-facing sprite for one pokemon."""
    # Open the JSON file we already downloaded for this pokemon, rather
    # than asking the API again -- we only need it for the image URLs.
    data = RAW_POKEMON_DIR / f'{pokemon_id}.json'
    with open(data) as f:
        pokemon_data = json.load(f)
    sprites_json = pokemon_data['sprites']

    os.makedirs(SPRITES_DIR, exist_ok=True)

    for sprite_name, url in sprites_json.items():
        # The sprites section has nested groups inside it ("other",
        # "versions") holding artwork we don't want. Those come through as
        # dicts rather than plain URL strings, so skipping dicts skips them.
        if isinstance(url, dict):
            continue

        # Skip anything with no image, and skip back-facing sprites.
        if url is None or "back" in sprite_name:
            continue

        # Same retry-with-a-growing-wait idea as in pokeapi_rip.py:
        # try 3 times, waiting 1s then 2s, before giving up on this image.
        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=5)
                if response.status_code == 200:
                    # "wb" = write BINARY. Images aren't text, so we write
                    # the raw bytes rather than a string.
                    filename = SPRITES_DIR / f'{pokemon_id}_{sprite_name}.png'
                    with open(filename, 'wb') as f:
                        f.write(response.content)
                    break  # got it, stop retrying
                else:
                    if attempt < max_retries - 1:
                        time.sleep(retry_delay)
                        retry_delay *= 2

            except requests.exceptions.RequestException:
                # Network problem rather than a bad response. Same plan.
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    retry_delay *= 2


# ---------------------------------------------------------------
# Get the list of every pokemon id from the database, then fetch
# sprites for each one in turn.
# ---------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
cursor = conn
ids = pd.DataFrame(cursor.execute('select id, name from pokemon'), columns=["id", 'name'])
conn.close()

print(ids.head())
count = 0

for id in ids['id']:
    count += 1
    download_sprites(id)
    # Progress line, so you can see it's still alive during a long run.
    print(f'got sprites for {count}/{len(ids)}')
