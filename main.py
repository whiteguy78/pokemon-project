"""
The web server.

This is the part that runs while you're using the Pokedex. It does two jobs:

  1. Hands the browser the actual web page (the HTML/CSS/JS in static/).
  2. Answers questions from that page, like "give me everything about
     pokemon #6" -- those are the /api/... routes further down.

It does NOT build any data. All the data was already built once by the
scripts in prep/ and saved into data/. This file only ever READS.

To run it:
    python3 main.py
Then open http://localhost:8000 in a browser.
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pokedex_queries import Pokedex
from pathlib import Path
import os
import json
import requests

app = FastAPI()

# Where things live on disk.
#
# We work out these paths from THIS file's own location rather than just
# writing "data/maps/..." and hoping. If we used plain relative paths, the
# server would only work if you happened to launch it from exactly the
# right folder. This way it works from anywhere.
PROJECT_DIR = Path(__file__).resolve().parent      # .../pokemon_project
STATIC_DIR = PROJECT_DIR / "static"                # the web page files
DATA_DIR = PROJECT_DIR / "data"                    # everything prep/ built
SPRITES_DIR = DATA_DIR / "sprites"                 # the pokemon .png images
MAPS_DIR = DATA_DIR / "maps"                       # pin coordinates (json)

# This makes everything in static/ available at http://localhost:8000/static/...
# So static/style.css becomes http://localhost:8000/static/style.css
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Same idea, but for sprite images: data/sprites/6_front_default.png
# becomes http://localhost:8000/sprites/6_front_default.png
app.mount("/sprites", StaticFiles(directory=SPRITES_DIR), name="sprites")

# Encounter data (where a pokemon is found in the wild) is the one thing we
# didn't download up front, so we fetch it on demand and keep a copy here
# so we only ever fetch each pokemon once. See get_encounters() at the bottom.
ENCOUNTERS_CACHE_DIR = DATA_DIR / "raw" / "encounters"

# The four sprite pictures a pokemon might have. Not every pokemon has all
# four (only some have a visibly different female form, for example).
SPRITE_TYPES = ["front_default", "front_shiny", "front_female", "front_shiny_female"]

# Which region does each generation of games take place in? Gen 1 is Kanto,
# gen 2 is Johto, and so on. (700 is a fake generation number we invent
# below for Let's Go -- keep reading.)
GENERATION_TO_REGION = {
    1: "kanto", 2: "johto", 3: "hoenn", 4: "sinnoh", 5: "unova",
    6: "kalos", 7: "alola", 8: "galar", 9: "paldea",
    700: "kanto",  # Let's Go Pikachu/Eevee -- see LETS_GO_GEN_ID below
}

# Every region now has a real map SVG traced/pixelated from the user's
# reference images in "images for claude/" (see prep/pixelate_map.py).
REGIONS_WITH_REAL_MAPS = {
    "kanto", "johto", "hoenn", "sinnoh", "unova", "kalos", "paldea", "alola", "galar",
}

# Load every region's pin coordinates into memory once, at startup, instead
# of re-reading the files on every single request. A "pin" is just an x/y
# percentage saying where to draw a dot on that region's map.
REGION_PINS = {}
for region in GENERATION_TO_REGION.values():
    with open(MAPS_DIR / f"{region}_pins.json") as f:
        REGION_PINS[region] = json.load(f)

# location-area slug -> the region it's ACTUALLY in. A game's generation
# doesn't tell you its region: FireRed/LeafGreen are gen 3 but set in
# Kanto, HeartGold/SoulSilver are gen 4 but set in Johto+Kanto, ORAS are
# gen 6 but set in Hoenn, and GSC reach Kanto in the postgame. Without
# this, those games show the wrong region's map and resolve no pins at
# all. Built by prep/build_area_regions.py.
with open(MAPS_DIR / "location_area_regions.json") as f:
    AREA_TO_REGION = json.load(f)


def clean_name(raw_name):
    # PokeAPI names are lowercase with dashes, like "mr-mime" or "solar-power"
    # We want "Mr Mime" or "Solar Power" for display. Doing this once here
    # means the frontend never has to think about hyphens/casing.
    if raw_name is None:
        return raw_name
    return raw_name.replace("-", " ").title()


def bucket_title(region, generation_name):
    # Label for one map tab, e.g. "Kanto · Gen III". The region matters
    # more than the generation here (that's what the map shows), but the
    # generation still disambiguates e.g. Kanto in Gen I vs Gen III.
    short = generation_name.replace("Generation ", "Gen ")
    if region is None:
        return short
    region_label = clean_name(region)
    if region_label.lower() in short.lower():
        return short  # e.g. "Let's Go (Kanto)" already names the region
    return f"{region_label} · {short}"


def clean_generation_name(raw_name):
    # clean_name() alone turns "generation-ii" into "Generation Ii" --
    # .title() doesn't know roman numerals aren't regular words. Fix up
    # just the numeral part afterward.
    cleaned = clean_name(raw_name)
    words = cleaned.split(" ")
    words[-1] = words[-1].upper()
    return " ".join(words)


# version name -> (generation_id, generation display name), so encounter
# locations can be grouped into per-generation tabs on the map carousel.
# Built once at startup: it's a small table that never changes, so there's
# no reason to ask the database for it on every request.
_db = Pokedex()
VERSION_TO_GENERATION = {}
for _row in _db.cursor.execute(
    """SELECT v.name AS version_name, g.id AS gen_id, g.name AS gen_name
       FROM version v JOIN generation g ON v.generation_id = g.id"""
):
    VERSION_TO_GENERATION[_row["version_name"]] = (_row["gen_id"], clean_generation_name(_row["gen_name"]))
_db.close()

# Let's Go Pikachu/Eevee share generation-number 7 with Sun/Moon/Ultra in the
# DB, but they're set in Kanto, not Alola -- bucket them under a synthetic
# generation id so the map carousel doesn't show Alola's map for Kanto
# locations (see GENERATION_TO_REGION above).
LETS_GO_GEN_ID = 700
for _v in ("lets-go-pikachu", "lets-go-eevee"):
    if _v in VERSION_TO_GENERATION:
        VERSION_TO_GENERATION[_v] = (LETS_GO_GEN_ID, "Let's Go (Kanto)")


def find_available_sprites(pokemon_id):
    # Check disk for which of the 4 possible sprite variants actually
    # exist for this pokemon id (works for both base pokemon and
    # mega/gmax/regional variant ids -- they're all just files named
    # "{id}_{type}.png" in data/sprites).
    available = []
    for sprite_type in SPRITE_TYPES:
        filename = f"{pokemon_id}_{sprite_type}.png"
        if os.path.exists(SPRITES_DIR / filename):
            available.append({"type": sprite_type, "url": f"/sprites/{filename}"})
    return available


def describe_trigger(trigger):
    # Turns {trigger_type, trigger_level, trigger_item} into one readable
    # label for the arrow in the evolution flow chart.
    if trigger is None:
        return None
    if trigger.get("trigger_level"):
        return f"Level {trigger['trigger_level']}"
    if trigger.get("trigger_item"):
        return f"Use {clean_name(trigger['trigger_item'])}"
    if trigger.get("trigger_type") == "trade":
        return "Trade"
    return clean_name(trigger.get("trigger_type")) or "Special"


def find_path_and_node(tree, target_id, path=None):
    # DFS from the root looking for target_id; returns (path_of_ids, node)
    # where path is root -> ... -> target_id.
    #
    # In plain English: the evolution tree is a family tree. This walks it
    # top to bottom hunting for one specific pokemon, and hands back both
    # that pokemon AND the trail of names it took to get there.
    path = (path or []) + [tree["id"]]
    if tree["id"] == target_id:
        return path, tree
    for child in tree["children"]:
        found_path, found_node = find_path_and_node(child, target_id, path)
        if found_node is not None:
            return found_path, found_node
    return None, None


def collect_descendant_ids(node):
    # Everything at or below this point in the family tree.
    # Charmeleon -> {charmeleon, charizard}.
    ids = {node["id"]}
    for child in node["children"]:
        ids |= collect_descendant_ids(child)
    return ids


def enrich_evolution_node(node, current_id, on_path_ids):
    # Walks the whole evolution tree once, adding everything the frontend
    # needs to draw it: display name, sprite, whether this IS the pokemon
    # being viewed, whether it's on that pokemon's direct line (vs. a
    # sibling branch like an alternate Eeveelution), and a readable label
    # for the trigger that leads INTO this node.
    node["display_name"] = clean_name(node["name"])
    sprites = find_available_sprites(node["id"])
    node["sprite"] = sprites[0]["url"] if sprites else None
    node["is_current"] = node["id"] == current_id
    node["on_path"] = node["id"] in on_path_ids
    node["trigger_description"] = describe_trigger(node["trigger"])
    for child in node["children"]:
        enrich_evolution_node(child, current_id, on_path_ids)


# ===================================================================
# ROUTES -- the URLs this server answers to.
#
# The "@app.get(...)" line above each function says: when a browser asks
# for this URL, run this function and send back whatever it returns.
# FastAPI turns any dict we return into JSON automatically.
# ===================================================================


@app.get("/")
def serve_homepage():
    # When someone visits http://localhost:8000/, send them the HTML file.
    # The browser then runs script.js, which calls the API routes below.
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/pokedex")
def serve_pokedex_theme():
    # Same #app content and same script.js as "/" -- just wrapped in
    # handheld-Pokedex device chrome via pokedex.html + style-pokedex.css.
    return FileResponse(STATIC_DIR / "pokedex.html")


@app.get("/api/meta")
def get_meta():
    # Small endpoint for numbers the frontend needs but shouldn't have to
    # recompute: dex bounds (for the flip buttons) and the real min/max of
    # each stat across every pokemon (for the stat bar gradients).
    db = Pokedex()
    row = db.cursor.execute(
        "SELECT MIN(national_dex_no), MAX(national_dex_no) FROM pokemon"
    ).fetchone()

    stat_ranges = {}
    for stat in ["hp", "attack", "defense", "sp_atk", "sp_def", "speed"]:
        stat_row = db.cursor.execute(
            f"SELECT MIN({stat}), MAX({stat}) FROM pokemon_battle_stats"
        ).fetchone()
        stat_ranges[stat] = {"min": stat_row[0], "max": stat_row[1]}

    db.close()
    return {"min_dex_no": row[0], "max_dex_no": row[1], "stat_ranges": stat_ranges}


@app.get("/api/search")
def search_pokemon(q: str):
    # q is a query parameter, e.g. /api/search?q=char -> q = "char"
    # This is what fills the type-ahead dropdown as you type.
    db = Pokedex()
    results = db.search_pokemon(q)
    db.close()

    # Clean up names for display in the dropdown too
    for result in results:
        result["display_name"] = clean_name(result["name"])

    return results


@app.get("/api/pokemon/{dex_no}")
def get_pokemon(dex_no: int):
    # The big one. Everything the page needs about one pokemon, in a
    # single response, so the browser only has to ask once.
    #
    # dex_no comes from the URL, e.g. /api/pokemon/6 -> dex_no = 6
    # FastAPI automatically converts it to an int for us (that's the ": int" part)
    db = Pokedex()
    pokemon = db.get_full_pokemon(dex_no)

    if pokemon is None:
        db.close()
        return {"error": f"No pokemon found with dex number {dex_no}"}

    # Merge in moves from earlier evolution stages that this pokemon's OWN
    # movepool doesn't already include (in practice most are already
    # inherited, but a few slip through), each tagged with a sprite of
    # whichever earlier-stage pokemon actually learns it so the frontend
    # can show a small "learned by X" icon.

    # Start by marking every move as "this pokemon learns it itself"
    # (no source pokemon, no little sprite next to it).
    for move in pokemon["moves"]:
        move["source_pokemon_name"] = None
        move["source_sprite"] = None

    # Then walk back up the evolution line -- Charizard -> Charmeleon ->
    # Charmander -- and pull in anything we don't already have.
    known_move_names = {m["move_name"] for m in pokemon["moves"]}
    for ancestor_id in db.get_pre_evolution_ids(pokemon["id"]):
        ancestor_row = db.cursor.execute("SELECT name FROM pokemon WHERE id = ?", (ancestor_id,)).fetchone()
        if not ancestor_row:
            continue
        ancestor_sprites = find_available_sprites(ancestor_id)
        ancestor_sprite_url = ancestor_sprites[0]["url"] if ancestor_sprites else None

        for row in db.get_moves(ancestor_id):
            move = dict(row)
            if move["move_name"] in known_move_names:
                continue  # already have it, skip
            known_move_names.add(move["move_name"])
            move["source_pokemon_name"] = clean_name(ancestor_row["name"])
            move["source_sprite"] = ancestor_sprite_url
            pokemon["moves"].append(move)

    # Sort the whole combined list: level-up moves first (in the order
    # you'd actually learn them), then everything else grouped by method.
    pokemon["moves"].sort(key=lambda m: (
        0 if m["learn_method"] == "level-up" else 1,
        m["level_learned"] or 0,
        m["learn_method"] or "",
        m["move_name"] or "",
    ))

    db.close()

    # Clean up the name before sending it to the frontend
    pokemon["display_name"] = clean_name(pokemon["name"])

    # Clean up every other hyphenated/lowercase label in the payload so the
    # frontend can just drop these strings straight into the page.
    pokemon["stats"]["type1"] = clean_name(pokemon["stats"]["type1"])
    pokemon["stats"]["type2"] = clean_name(pokemon["stats"]["type2"])

    pokemon["biological"]["color"] = clean_name(pokemon["biological"]["color"])
    pokemon["biological"]["habitat"] = clean_name(pokemon["biological"]["habitat"])

    for ability in pokemon["abilities"]:
        ability["ability_name"] = clean_name(ability["ability_name"])

    pokemon["egg_groups"] = [clean_name(g) for g in pokemon["egg_groups"]]

    for move in pokemon["moves"]:
        move["move_name"] = clean_name(move["move_name"])
        move["learn_method"] = clean_name(move["learn_method"])
        move["move_type"] = clean_name(move["move_type"])

    for tm in pokemon["tm_hm_moves"]:
        tm["move_name"] = clean_name(tm["move_name"])
        tm["move_type"] = clean_name(tm["move_type"])

    for form in pokemon["forms"]:
        form["form_name"] = clean_name(form["form_name"])
        form["type1"] = clean_name(form["type1"])
        form["type2"] = clean_name(form["type2"])
        # each form's own sprites, so the Forms tab can show a thumbnail
        form["sprites_available"] = find_available_sprites(form["variant_pokemon_id"])

    # Work out which parts of the evolution tree are on THIS pokemon's own
    # line (ancestors above it + everything below it) so the frontend can
    # grey out sibling branches -- e.g. viewing Vaporeon, the other seven
    # Eeveelutions are cousins, not part of its line.
    ancestor_path, current_node = find_path_and_node(pokemon["evolution"], pokemon["id"])
    on_path_ids = set(ancestor_path or [])
    if current_node:
        on_path_ids |= collect_descendant_ids(current_node)
    enrich_evolution_node(pokemon["evolution"], pokemon["id"], on_path_ids)

    # Tag each entry with the generation of the game it's from, so the
    # frontend can swing the map to the matching region as you page
    # through pokedex entries. Read before clean_name() -- the lookup
    # table is keyed on the raw slug.
    for desc in pokemon["descriptions"]:
        gen_id, _ = VERSION_TO_GENERATION.get(desc["version"], (None, None))
        desc["generation_id"] = gen_id
        desc["version"] = clean_name(desc["version"])

    pokemon["sprites_available"] = find_available_sprites(pokemon["id"])

    return pokemon


@app.get("/api/pokemon-variant/{variant_id}")
def get_pokemon_variant(variant_id: int):
    # Used when the user clicks a Mega/Gmax/regional form in the Forms tab.
    # variant_id is the form's OWN pokemon id (e.g. 10034 for Mega Charizard X),
    # not a dex number -- these forms don't have national dex numbers of
    # their own.
    db = Pokedex()
    variant = db.get_variant(variant_id)
    db.close()

    if variant is None:
        return {"error": f"No variant found with id {variant_id}"}

    variant["display_name"] = clean_name(variant["name"])
    variant["stats"]["type1"] = clean_name(variant["stats"]["type1"])
    variant["stats"]["type2"] = clean_name(variant["stats"]["type2"])

    for ability in variant["abilities"]:
        ability["ability_name"] = clean_name(ability["ability_name"])

    variant["sprites_available"] = find_available_sprites(variant_id)

    return variant


@app.get("/api/pokemon/{dex_no}/encounters")
def get_encounters(dex_no: int):
    # Where in the world you can catch this pokemon.
    #
    # There's no bulk-downloaded encounter data on disk (it's a separate
    # endpoint PokeAPI doesn't include in the main pokemon payload), so we
    # fetch it live the first time and cache it to disk afterward -- same
    # pattern as prep/sprite_rip.py used for sprites.
    os.makedirs(ENCOUNTERS_CACHE_DIR, exist_ok=True)
    cache_path = ENCOUNTERS_CACHE_DIR / f"{dex_no}.json"

    if os.path.exists(cache_path):
        # Seen this pokemon before -- just read our saved copy.
        with open(cache_path) as f:
            raw_encounters = json.load(f)
    else:
        # First time. Ask PokeAPI, and don't fall over if the internet is
        # down or slow -- an empty list just means "no locations shown".
        try:
            response = requests.get(
                f"https://pokeapi.co/api/v2/pokemon/{dex_no}/encounters", timeout=5
            )
            raw_encounters = response.json() if response.status_code == 200 else []
        except requests.exceptions.RequestException:
            raw_encounters = []

        with open(cache_path, "w") as f:
            json.dump(raw_encounters, f)

    # Group into one bucket per (GENERATION, REGION) so the map carousel
    # can page through tabs that each correspond to exactly one map. It's
    # keyed on region as well as generation because a single generation
    # can span two regions -- HeartGold/SoulSilver (gen 4) cover Johto
    # AND Kanto, and no single map can show both. A location can also
    # appear in several generations (Viridian Forest is in Red/Blue *and*
    # FireRed/LeafGreen), so it's bucketed once per generation it appears
    # in, with its version list filtered to just that generation's games.
    buckets = {}  # (gen_id, region) -> {generation_id, region, generation, locations, map}

    for entry in raw_encounters:
        raw_slug = entry.get("location_area", {}).get("name")
        location_name = clean_name(raw_slug)
        if not location_name:
            continue

        # Which games mention this location at all?
        raw_versions = {vd.get("version", {}).get("name") for vd in entry.get("version_details", [])}

        # Split those games up by which generation they belong to.
        versions_by_gen = {}
        for v in raw_versions:
            gen_id, gen_name = VERSION_TO_GENERATION.get(v, (None, "Unknown"))
            versions_by_gen.setdefault((gen_id, gen_name), []).append(v)

        area_region = AREA_TO_REGION.get(raw_slug)

        for (gen_id, gen_name), gen_versions in versions_by_gen.items():
            # The location's own region is authoritative; the generation's
            # region is only a fallback for slugs missing from the index.
            region = area_region or GENERATION_TO_REGION.get(gen_id)

            # Do we know where to draw a dot for this place? Not every
            # location has a hand-placed pin -- see data/maps/README.md.
            pin = None
            if region in REGION_PINS and raw_slug in REGION_PINS[region]:
                p = REGION_PINS[region][raw_slug]
                pin = {"x": p["x"], "y": p["y"]}

            # setdefault = "get this bucket, or make an empty one first"
            bucket = buckets.setdefault((gen_id, region), {
                "generation_id": gen_id,
                "region": region,
                "generation": bucket_title(region, gen_name),
                "locations": [],
                "map": region if region in REGIONS_WITH_REAL_MAPS else None,
            })
            bucket["locations"].append({
                "location": location_name,
                "versions": sorted(clean_name(v) for v in gen_versions),
                "pin": pin,
            })

    # Oldest generation first, so the tabs read left-to-right in game order.
    generation_list = sorted(
        buckets.values(),
        key=lambda g: (g["generation_id"] is None, g["generation_id"], g["region"] or "")
    )

    return {"generations": generation_list}


def slugify(display_name):
    # Reverses clean_name(): "Solar Power" -> "solar-power". Works because
    # clean_name is just replace("-", " ").title(), so lowercasing and
    # swapping spaces back to hyphens gets us back to the original slug.
    return display_name.lower().replace(" ", "-")


@app.get("/api/move-detail/{move_display_name}")
def get_move_detail(move_display_name: str):
    # Called when you tap a move -- fills the little detail popup.
    db = Pokedex()
    move = db.get_move_detail(slugify(move_display_name))
    db.close()

    if move is None:
        return {"error": f"No move found: {move_display_name}"}

    move["display_name"] = clean_name(move["name"])
    move["type"] = clean_name(move["type"])
    move["damage_class"] = clean_name(move["damage_class"])
    return move


@app.get("/api/ability-detail/{ability_display_name}")
def get_ability_detail(ability_display_name: str):
    # Same as above, but for abilities.
    db = Pokedex()
    ability = db.get_ability_detail(slugify(ability_display_name))
    db.close()

    if ability is None:
        return {"error": f"No ability found: {ability_display_name}"}

    ability["display_name"] = clean_name(ability["name"])
    return ability


@app.get("/api/type-chart")
def get_type_chart():
    # The full 18x18 "fire beats grass" table. The frontend asks for this
    # once and remembers it, since it's the same for every pokemon.
    db = Pokedex()
    chart = db.get_type_chart()
    db.close()
    return chart


# This block only runs if you start the file directly ("python3 main.py").
# It doesn't run if something else imports this file.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
