#!/usr/bin/env python3
"""
STEP 2 of the data pipeline: turn the downloaded JSON into a real database.

prep/pokeapi_rip.py left us with roughly 100,000 loose JSON files in
data/raw/. That's fine for storage but hopeless for an app -- you can't
ask a folder of files "which pokemon are part Flying type and learn Surf?".

So this script reads all of those files and pours the useful bits into a
proper SQLite database at data/pokemon.db, split across ~23 tables. That's
the file the web app actually reads.

A few things to know:

  - It DELETES and rebuilds data/pokemon.db from scratch every run. It's
    not an update, it's a fresh build. That's deliberate: a rebuild is
    cheap, and it means the database can never end up half-old-half-new.

  - PokeAPI's JSON is messy and inconsistent -- fields go missing, some
    records are odd shapes. So most loops here are wrapped in
    "try / except: pass", which means "if this one record is broken, skip
    it and keep going". You'd never do that in a bank; here, losing one
    weird record out of 100,000 is much better than the whole build dying
    at 3am on record 40,000.

  - "INSERT OR IGNORE" means "add this row, unless one with the same
    primary key is already there". Saves having to check first.

Run:  python3 prep/build_pokedex_db.py
"""
import json
import sqlite3
from pathlib import Path
from collections import defaultdict
import re
import sys

# This file lives in prep/, so the project root is one level up.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data" / "raw"      # what step 1 downloaded
DB_PATH = PROJECT_DIR / "data" / "pokemon.db"  # what we're building


# ============================================================
# LITTLE HELPERS
# PokeAPI has a few shapes that show up over and over, so rather than
# unpacking them by hand fifty times, they get a function each.
# ============================================================

def extract_id_from_url(url):
    """Extract numeric ID from PokeAPI URL."""
    # PokeAPI hands you links instead of ids all over the place, e.g.
    # "https://pokeapi.co/api/v2/ability/65/". We just want the 65.
    # The regex says: a slash, then digits, then a slash, at the very end.
    if url:
        match = re.search(r'/(\d+)/$', url)
        if match:
            return int(match.group(1))
    return None


def get_name_from_obj(obj):
    """Extract name from a nested {name, url} object."""
    # Almost every reference in PokeAPI looks like
    # {"name": "fire", "url": "https://..."} -- this safely pulls the name
    # out, and returns None if it got handed something unexpected.
    if isinstance(obj, dict):
        return obj.get("name")
    return None


def get_english_short_effect(data):
    """Pull the English short_effect out of a move/ability's effect_entries list."""
    # The same description exists in a dozen languages, all in one list.
    # Walk the list and take the English one.
    for entry in data.get("effect_entries", []):
        if get_name_from_obj(entry.get("language")) == "en":
            return entry.get("short_effect")
    return None


def get_latest_english_flavor_text(data):
    """Pull the most recent English flavor_text out of a move's
    flavor_text_entries list -- pokeapi lists these oldest-game-first, so
    the last English entry is the newest (most modern wording)."""
    # No "break" here on purpose: we keep overwriting `text` with each
    # English entry we find, so we end up holding the LAST one.
    text = None
    for entry in data.get("flavor_text_entries", []):
        if get_name_from_obj(entry.get("language")) == "en":
            text = entry.get("flavor_text")
    if text:
        # Game text is full of junk characters: soft hyphens (\xad) and
        # hard line breaks baked in for the original screen widths.
        # Strip them out and squash the leftover spacing.
        text = text.replace("\xad", "").replace("\n", " ").replace("\f", " ")
        text = " ".join(text.split())
    return text


class PokedexDB:
    """Holds the database connection and one method per chunk of the build."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.stats_map = {}  # id -> name mapping for stats
        self.move_types = {}  # move name -> type name, filled in load_reference_data

    def create_tables(self):
        """Create all database tables."""
        # executescript() runs a whole block of SQL at once, so the entire
        # schema can live in one string. Read this as the blueprint for
        # the finished database -- every table the app queries is here.
        #
        # The general shape: one "pokemon" table holding identity, and a
        # satellite table for each kind of fact about a pokemon, joined
        # back by pokemon_id. That way a pokemon with 200 moves doesn't
        # need 200 columns.
        self.cursor.executescript("""
        -- Core Pokemon table
        CREATE TABLE IF NOT EXISTS pokemon (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            national_dex_no INTEGER UNIQUE,
            generation_id INTEGER
        );

        -- Stats for each Pokemon (one row per pokemon)
        CREATE TABLE IF NOT EXISTS pokemon_battle_stats (
            pokemon_id INTEGER PRIMARY KEY,
            hp INTEGER,
            attack INTEGER,
            defense INTEGER,
            sp_atk INTEGER,
            sp_def INTEGER,
            speed INTEGER,
            type1 TEXT,
            type2 TEXT,
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Biological/Physical data (one row per pokemon)
        CREATE TABLE IF NOT EXISTS pokemon_biological (
            pokemon_id INTEGER PRIMARY KEY,
            height INTEGER,
            weight INTEGER,
            shape TEXT,
            color TEXT,
            habitat TEXT,
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Descriptions/Flavor text (one row per version+language combo)
        CREATE TABLE IF NOT EXISTS pokemon_descriptions (
            pokemon_id INTEGER,
            version TEXT,
            language TEXT,
            text TEXT,
            PRIMARY KEY (pokemon_id, version, language),
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Moves learned by Pokemon (long format)
        CREATE TABLE IF NOT EXISTS pokemon_moves (
            pokemon_id INTEGER,
            move_id INTEGER,
            move_name TEXT,
            level_learned INTEGER,
            learn_method TEXT,
            PRIMARY KEY (pokemon_id, move_id, level_learned, learn_method),
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Abilities (long format)
        CREATE TABLE IF NOT EXISTS pokemon_abilities (
            pokemon_id INTEGER,
            ability_id INTEGER,
            ability_name TEXT,
            slot INTEGER,
            is_hidden BOOLEAN,
            PRIMARY KEY (pokemon_id, ability_id),
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Egg groups (long format)
        CREATE TABLE IF NOT EXISTS pokemon_egg_groups (
            pokemon_id INTEGER,
            egg_group_name TEXT,
            PRIMARY KEY (pokemon_id, egg_group_name),
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Alternate forms (regional variants, megas, gmax, etc.)
        -- base_pokemon_id is the "home" species this form appears under
        -- (e.g. 6 for charizard). variant_pokemon_id is the form's OWN
        -- pokemon id (e.g. 10034 for charizard-mega-x) -- that id is what
        -- its sprite files on disk and its own stats/types are keyed by.
        CREATE TABLE IF NOT EXISTS pokemon_forms (
            form_id INTEGER PRIMARY KEY,
            base_pokemon_id INTEGER,
            variant_pokemon_id INTEGER,
            form_name TEXT,
            is_mega BOOLEAN,
            type1 TEXT,
            type2 TEXT,
            height REAL,
            weight REAL,
            order_in_form INTEGER,
            FOREIGN KEY(base_pokemon_id) REFERENCES pokemon(id)
        );

        -- TMs/HMs a pokemon can learn (separate from level-up/egg/tutor moves)
        CREATE TABLE IF NOT EXISTS pokemon_tm_hm (
            pokemon_id INTEGER,
            move_name TEXT,
            move_type TEXT,
            tm_code TEXT,
            version_group TEXT,
            PRIMARY KEY (pokemon_id, move_name, version_group),
            FOREIGN KEY(pokemon_id) REFERENCES pokemon(id)
        );

        -- Evolution chains
        CREATE TABLE IF NOT EXISTS pokemon_evolutions (
            evolves_from_id INTEGER,
            evolves_to_id INTEGER,
            trigger_type TEXT,
            trigger_item TEXT,
            trigger_level INTEGER,
            condition TEXT,
            PRIMARY KEY (evolves_from_id, evolves_to_id),
            FOREIGN KEY(evolves_from_id) REFERENCES pokemon(id),
            FOREIGN KEY(evolves_to_id) REFERENCES pokemon(id)
        );

        -- Reference tables
        CREATE TABLE IF NOT EXISTS type (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        -- Full attack-type x defend-type effectiveness matrix, e.g.
        -- (Fire, Grass, 2.0) means Fire attacks deal 2x to Grass pokemon.
        -- Every pair gets a row (defaulting to 1.0) so lookups never miss.
        CREATE TABLE IF NOT EXISTS type_matchup (
            attacking_type TEXT,
            defending_type TEXT,
            multiplier REAL,
            PRIMARY KEY (attacking_type, defending_type)
        );

        CREATE TABLE IF NOT EXISTS move (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            power INTEGER,
            accuracy INTEGER,
            pp INTEGER,
            type TEXT,
            damage_class TEXT,
            short_effect TEXT,
            flavor_text TEXT
        );

        CREATE TABLE IF NOT EXISTS ability (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            short_effect TEXT
        );

        CREATE TABLE IF NOT EXISTS egg_group (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pokemon_habitat (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pokemon_shape (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pokemon_color (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS pokemon_species (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS stat (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS generation (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        -- sort_order comes from the version's version-group ("red-blue" etc,
        -- which itself has an "order" field pokeapi uses for release order).
        -- This is what lets us show pokedex entries oldest-game-first
        -- instead of alphabetically.
        CREATE TABLE IF NOT EXISTS version (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            sort_order INTEGER,
            generation_id INTEGER
        );

        CREATE TABLE IF NOT EXISTS language (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS learn_method (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS evolution_trigger (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL
        );
        """)
        self.conn.commit()
        print("✓ Tables created")

    def load_reference_data(self):
        """Load all reference tables first."""
        # "Reference data" = the lookup lists that everything else points
        # at: the 18 types, every move, every ability, the list of games,
        # and so on. These have to go in FIRST, because the pokemon rows
        # loaded later refer back to them.
        #
        # Every block below follows the same shape:
        #   look in a folder -> read each .json -> insert one row.
        # It's repetitive, and that's fine; it's easier to read than a
        # clever generic version would be.
        print("\nLoading reference data...")

        # Types, plus the full attack/defend effectiveness matrix. Every
        # type starts at 1.0 against everything, then damage_relations
        # overrides specific pairs to 2.0 / 0.5 / 0.0.
        ALL_TYPE_NAMES = [
            "normal", "fire", "water", "electric", "grass", "ice", "fighting",
            "poison", "ground", "flying", "psychic", "bug", "rock", "ghost",
            "dragon", "dark", "steel", "fairy",
        ]
        type_dir = DATA_DIR / "type"
        if type_dir.exists():
            for f in type_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    attacking_type = data.get("name")
                    self.cursor.execute("INSERT OR IGNORE INTO type (id, name) VALUES (?, ?)",
                                      (data.get("id"), attacking_type))

                    if attacking_type not in ALL_TYPE_NAMES:
                        continue  # skip non-standard/past types (e.g. "unknown", "shadow")

                    # Start by assuming this type does normal damage (1x)
                    # to all 18 types, then overwrite the exceptions.
                    # Filling in every pair means the app can look up any
                    # combination without ever getting a missing value.
                    multipliers = {defending: 1.0 for defending in ALL_TYPE_NAMES}
                    relations = data.get("damage_relations", {})
                    for defending in relations.get("double_damage_to", []):
                        multipliers[get_name_from_obj(defending)] = 2.0
                    for defending in relations.get("half_damage_to", []):
                        multipliers[get_name_from_obj(defending)] = 0.5
                    for defending in relations.get("no_damage_to", []):
                        multipliers[get_name_from_obj(defending)] = 0.0

                    for defending_type, multiplier in multipliers.items():
                        self.cursor.execute(
                            """INSERT OR IGNORE INTO type_matchup
                               (attacking_type, defending_type, multiplier)
                               VALUES (?, ?, ?)""",
                            (attacking_type, defending_type, multiplier)
                        )
                except:
                    pass  # broken file -- skip it, keep going (see module docstring)
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM type").fetchone()[0]
            matchup_count = self.cursor.execute("SELECT COUNT(*) FROM type_matchup").fetchone()[0]
            print(f"  ✓ Types: {count} ({matchup_count} matchup pairs)")

        # Moves
        move_dir = DATA_DIR / "move"
        if move_dir.exists():
            for f in move_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    move_name = data.get("name")
                    move_type = get_name_from_obj(data.get("type"))
                    short_effect = get_english_short_effect(data)
                    flavor_text = get_latest_english_flavor_text(data)
                    self.cursor.execute(
                        """INSERT OR IGNORE INTO move
                           (id, name, power, accuracy, pp, type, damage_class, short_effect, flavor_text)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (data.get("id"), move_name, data.get("power"), data.get("accuracy"),
                         data.get("pp"), move_type,
                         get_name_from_obj(data.get("damage_class")), short_effect, flavor_text)
                    )
                    # cache move -> type so load_tm_hm() doesn't need a DB
                    # lookup per row later
                    self.move_types[move_name] = move_type
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM move").fetchone()[0]
            print(f"  ✓ Moves: {count}")

        # Abilities
        ability_dir = DATA_DIR / "ability"
        if ability_dir.exists():
            for f in ability_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    short_effect = get_english_short_effect(data)
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO ability (id, name, short_effect) VALUES (?, ?, ?)",
                        (data.get("id"), data.get("name"), short_effect)
                    )
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM ability").fetchone()[0]
            print(f"  ✓ Abilities: {count}")

        # Egg groups
        egg_dir = DATA_DIR / "egg-group"
        if egg_dir.exists():
            for f in egg_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO egg_group (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM egg_group").fetchone()[0]
            print(f"  ✓ Egg groups: {count}")

        # Habitats
        habitat_dir = DATA_DIR / "pokemon-habitat"
        if habitat_dir.exists():
            for f in habitat_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO pokemon_habitat (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM pokemon_habitat").fetchone()[0]
            print(f"  ✓ Habitats: {count}")

        # Shapes
        shape_dir = DATA_DIR / "pokemon-shape"
        if shape_dir.exists():
            for f in shape_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO pokemon_shape (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM pokemon_shape").fetchone()[0]
            print(f"  ✓ Shapes: {count}")

        # Colors
        color_dir = DATA_DIR / "pokemon-color"
        if color_dir.exists():
            for f in color_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO pokemon_color (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM pokemon_color").fetchone()[0]
            print(f"  ✓ Colors: {count}")

        # Stats
        stat_dir = DATA_DIR / "stat"
        if stat_dir.exists():
            for f in stat_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    stat_id = data.get("id")
                    name = data.get("name")
                    self.cursor.execute("INSERT OR IGNORE INTO stat (id, name) VALUES (?, ?)",
                                      (stat_id, name))
                    if name:
                        self.stats_map[name] = stat_id
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM stat").fetchone()[0]
            print(f"  ✓ Stats: {count}")

        # Generations
        gen_dir = DATA_DIR / "generation"
        if gen_dir.exists():
            for f in gen_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO generation (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM generation").fetchone()[0]
            print(f"  ✓ Generations: {count}")

        # Versions -- each version (e.g. "red") belongs to a version-group
        # (e.g. "red-blue"), and the version-group is what actually carries
        # the release "order" and "generation". So first build a lookup of
        # version-group name -> (order, generation_id) from those files,
        # then use it while inserting each version.
        version_group_info = {}
        version_group_dir = DATA_DIR / "version-group"
        if version_group_dir.exists():
            for f in version_group_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    vg_name = data.get("name")
                    order = data.get("order")
                    gen_id = extract_id_from_url(data.get("generation", {}).get("url"))
                    version_group_info[vg_name] = (order, gen_id)
                except:
                    pass

        version_dir = DATA_DIR / "version"
        if version_dir.exists():
            for f in version_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    vg_name = get_name_from_obj(data.get("version_group"))
                    order, gen_id = version_group_info.get(vg_name, (None, None))
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO version (id, name, sort_order, generation_id) VALUES (?, ?, ?, ?)",
                        (data.get("id"), data.get("name"), order, gen_id)
                    )
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM version").fetchone()[0]
            print(f"  ✓ Versions: {count}")

        # Languages
        lang_dir = DATA_DIR / "language"
        if lang_dir.exists():
            for f in lang_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO language (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM language").fetchone()[0]
            print(f"  ✓ Languages: {count}")

        # Learn methods
        method_dir = DATA_DIR / "move-learn-method"
        if method_dir.exists():
            for f in method_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO learn_method (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM learn_method").fetchone()[0]
            print(f"  ✓ Learn methods: {count}")

        # Evolution triggers
        trigger_dir = DATA_DIR / "evolution-trigger"
        if trigger_dir.exists():
            for f in trigger_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    self.cursor.execute("INSERT OR IGNORE INTO evolution_trigger (id, name) VALUES (?, ?)",
                                      (data.get("id"), data.get("name")))
                except:
                    pass
            self.conn.commit()
            count = self.cursor.execute("SELECT COUNT(*) FROM evolution_trigger").fetchone()[0]
            print(f"  ✓ Evolution triggers: {count}")

    def load_pokemon_core(self):
        """Load Pokemon core data and species info."""
        # Reads data/raw/pokemon/*.json -- one file per pokemon (and per
        # alternate form, which PokeAPI also treats as its own "pokemon").
        # Fills in: the pokemon row itself, its six battle stats and types,
        # its height/weight, and its abilities.
        #
        # NOTE what's missing here: dex number, colour, habitat, egg groups
        # and pokedex descriptions. Those live on the SPECIES record, not
        # the pokemon record, so load_pokemon_species() adds them next.
        print("\nLoading Pokemon core data...")

        pokemon_dir = DATA_DIR / "pokemon"
        if not pokemon_dir.exists():
            print("  ✗ Pokemon folder not found")
            return

        loaded = 0
        for f in pokemon_dir.glob("*.json"):
            try:
                data = json.load(open(f))
                pokemon_id = data.get("id")
                name = data.get("name")

                if pokemon_id and name:
                    # Insert into pokemon table
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO pokemon (id, name) VALUES (?, ?)",
                        (pokemon_id, name)
                    )

                    # Stats (one row per pokemon).
                    # PokeAPI gives stats as a LIST of {name, value}, so
                    # flip it into a plain dict first -- much easier to
                    # pull named values out of when we insert below.
                    stats_dict = {}
                    for stat in data.get("stats", []):
                        stat_name = get_name_from_obj(stat.get("stat"))
                        stat_val = stat.get("base_stat")
                        if stat_name:
                            stats_dict[stat_name] = stat_val

                    # NOTE: Height and weight come as integers in decimeters/hectograms
                    # from the API, so we need to divide by 10 to get meters/kg
                    height_raw = data.get("height")
                    weight_raw = data.get("weight")
                    height = height_raw / 10 if height_raw else 0
                    weight = weight_raw / 10 if weight_raw else 0

                    self.cursor.execute(
                        """INSERT OR IGNORE INTO pokemon_battle_stats
                           (pokemon_id, hp, attack, defense, sp_atk, sp_def, speed, type1, type2)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (pokemon_id,
                         stats_dict.get("hp"),
                         stats_dict.get("attack"),
                         stats_dict.get("defense"),
                         stats_dict.get("special-attack"),
                         stats_dict.get("special-defense"),
                         stats_dict.get("speed"),
                         # type1 is always there; type2 only exists for
                         # dual-type pokemon, hence the length check.
                         get_name_from_obj(data.get("types", [{}])[0].get("type")) if data.get("types") else None,
                         get_name_from_obj(data.get("types", [{}, {}])[1].get("type")) if len(data.get("types", [])) > 1 else None)
                    )

                    # Store height/weight for species loading (already converted to floats)
                    self.cursor.execute(
                        """INSERT OR IGNORE INTO pokemon_biological
                           (pokemon_id, height, weight)
                           VALUES (?, ?, ?)""",
                        (pokemon_id, height, weight)
                    )

                    # Abilities
                    for ability in data.get("abilities", []):
                        ability_name = get_name_from_obj(ability.get("ability"))
                        ability_id = extract_id_from_url(ability.get("ability", {}).get("url"))
                        slot = ability.get("slot")
                        is_hidden = ability.get("is_hidden", False)
                        if ability_id and ability_name:
                            self.cursor.execute(
                                """INSERT OR IGNORE INTO pokemon_abilities
                                   (pokemon_id, ability_id, ability_name, slot, is_hidden)
                                   VALUES (?, ?, ?, ?, ?)""",
                                (pokemon_id, ability_id, ability_name, slot, is_hidden)
                            )

                    loaded += 1
                    if loaded % 100 == 0:
                        print(f"  Loaded {loaded} pokemon...")

            except Exception as e:
                pass  # skip this one file, carry on with the rest

        # Save everything in one go at the end. Committing after every
        # single insert would make this many times slower.
        self.conn.commit()
        print(f"  ✓ Loaded {loaded} Pokemon")

    def load_pokemon_species(self):
        """Load species data (descriptions, egg groups, habitat, etc.)."""
        # A "species" is the pokemon as a concept (Charizard), while a
        # "pokemon" is a specific body (Charizard, or Mega Charizard X).
        # PokeAPI splits them, so this pass UPDATEs the rows that
        # load_pokemon_core() already created, filling in the species-level
        # facts and adding descriptions + egg groups.
        print("\nLoading Pokemon species data...")

        species_dir = DATA_DIR / "pokemon-species"
        if not species_dir.exists():
            print("  ✗ Species folder not found")
            return

        loaded = 0
        desc_loaded = 0
        egg_loaded = 0

        for f in species_dir.glob("*.json"):
            try:
                data = json.load(open(f))
                species_id = data.get("id")

                # Update pokemon with national_dex_no and generation.
                # NOTE: the National Dex number IS the species id -- "order" is a
                # separate field pokeapi uses for pokedex listing/sort order and
                # does NOT match the actual dex number (they drift apart later
                # in the dex, e.g. vespiquen is dex #416 but order 444).
                gen_id = extract_id_from_url(data.get("generation", {}).get("url"))
                self.cursor.execute(
                    "UPDATE pokemon SET national_dex_no = ?, generation_id = ? WHERE id = ?",
                    (species_id, gen_id, species_id)
                )

                # Biological data - UPDATE existing record with color and habitat
                color_name = get_name_from_obj(data.get("color"))
                habitat_name = get_name_from_obj(data.get("habitat"))

                self.cursor.execute(
                    """UPDATE pokemon_biological
                       SET color = ?, habitat = ?
                       WHERE pokemon_id = ?""",
                    (color_name, habitat_name, species_id)
                )

                # Egg groups
                for egg_group in data.get("egg_groups", []):
                    egg_name = get_name_from_obj(egg_group)
                    if egg_name:
                        self.cursor.execute(
                            """INSERT OR IGNORE INTO pokemon_egg_groups
                               (pokemon_id, egg_group_name)
                               VALUES (?, ?)""",
                            (species_id, egg_name)
                        )
                        egg_loaded += 1

                # Flavor text entries (descriptions)
                for entry in data.get("flavor_text_entries", []):
                    text = entry.get("flavor_text", "").replace("\n", " ").replace("\f", " ")
                    version_name = get_name_from_obj(entry.get("version"))
                    lang_name = get_name_from_obj(entry.get("language"))
                    if text and version_name and lang_name:
                        self.cursor.execute(
                            """INSERT OR IGNORE INTO pokemon_descriptions
                               (pokemon_id, version, language, text)
                               VALUES (?, ?, ?, ?)""",
                            (species_id, version_name, lang_name, text)
                        )
                        desc_loaded += 1

                loaded += 1
                if loaded % 100 == 0:
                    print(f"  Processed {loaded} species...")

            except Exception as e:
                pass

        self.conn.commit()
        print(f"  ✓ Loaded {loaded} species, {egg_loaded} egg groups, {desc_loaded} descriptions")

    def load_pokemon_moves(self):
        """Load moves for each pokemon."""
        # Every pokemon file lists its moves, and every move lists every
        # game it appeared in and how it was learned there. We flatten all
        # of that into one long table: one row per
        # (pokemon, move, level, method).
        #
        # This is the biggest table in the database by a wide margin --
        # expect a few hundred thousand rows.
        print("\nLoading Pokemon moves...")

        pokemon_dir = DATA_DIR / "pokemon"
        if not pokemon_dir.exists():
            return

        loaded = 0
        for f in pokemon_dir.glob("*.json"):
            try:
                data = json.load(open(f))
                pokemon_id = data.get("id")

                for move in data.get("moves", []):
                    move_name = get_name_from_obj(move.get("move"))
                    move_id = extract_id_from_url(move.get("move", {}).get("url"))

                    for version in move.get("version_group_details", []):
                        level = version.get("level_learned_at")
                        method = get_name_from_obj(version.get("move_learn_method"))

                        if move_id and move_name and method:
                            self.cursor.execute(
                                """INSERT OR IGNORE INTO pokemon_moves
                                   (pokemon_id, move_id, move_name, level_learned, learn_method)
                                   VALUES (?, ?, ?, ?, ?)""",
                                (pokemon_id, move_id, move_name, level or 0, method)
                            )
                            loaded += 1

            except Exception as e:
                pass

        self.conn.commit()
        print(f"  ✓ Loaded {loaded} move records")

    def load_tm_hm(self):
        """
        Build the TM/HM list per pokemon. The pokemon jsons tell us WHICH
        moves are learned via "machine", but not the actual TM/HM number --
        that lives in data/raw/machine/*.json, which maps
        (move, version_group) -> item name (e.g. "tm05"). So step 1 is
        building that lookup, then step 2 walks pokemon moves again and
        joins against it.
        """
        print("\nBuilding TM/HM list...")

        # Step 1: build the lookup table of which TM number is which move.
        machine_lookup = {}  # (move_name, version_group_name) -> "tm05" / "hm01"
        machine_dir = DATA_DIR / "machine"
        if machine_dir.exists():
            for f in machine_dir.glob("*.json"):
                try:
                    data = json.load(open(f))
                    move_name = get_name_from_obj(data.get("move"))
                    vg_name = get_name_from_obj(data.get("version_group"))
                    item_name = get_name_from_obj(data.get("item"))
                    if move_name and vg_name and item_name:
                        machine_lookup[(move_name, vg_name)] = item_name
                except:
                    pass

        # Step 2: go back through the pokemon, and for every move they
        # learn "by machine", look up which TM that actually was.
        pokemon_dir = DATA_DIR / "pokemon"
        if not pokemon_dir.exists():
            return

        loaded = 0
        for f in pokemon_dir.glob("*.json"):
            try:
                data = json.load(open(f))
                pokemon_id = data.get("id")

                for move in data.get("moves", []):
                    move_name = get_name_from_obj(move.get("move"))

                    for version in move.get("version_group_details", []):
                        method = get_name_from_obj(version.get("move_learn_method"))
                        if method != "machine":
                            continue  # not a TM/HM, not our problem here

                        vg_name = get_name_from_obj(version.get("version_group"))
                        item_name = machine_lookup.get((move_name, vg_name))
                        if not item_name:
                            continue

                        # "tm05" -> "TM05", "hm01" -> "HM01"
                        tm_code = item_name.upper()
                        move_type = self.move_types.get(move_name)

                        self.cursor.execute(
                            """INSERT OR IGNORE INTO pokemon_tm_hm
                               (pokemon_id, move_name, move_type, tm_code, version_group)
                               VALUES (?, ?, ?, ?, ?)""",
                            (pokemon_id, move_name, move_type, tm_code, vg_name)
                        )
                        loaded += 1

            except Exception as e:
                pass

        self.conn.commit()
        print(f"  ✓ Loaded {loaded} TM/HM records")

    def load_evolutions(self):
        """Load evolution chains."""
        # PokeAPI stores evolutions as a nested tree per family: Eevee has
        # eight children, Charmander has one child that has one child.
        #
        # We flatten that tree into a simple table of pairs --
        # "A evolves into B, by this method" -- because pairs are far
        # easier to query. The app rebuilds the tree shape at read time
        # (see get_full_evolution_tree in app/pokedex_queries.py).
        print("\nLoading evolution chains...")

        evo_dir = DATA_DIR / "evolution-chain"
        if not evo_dir.exists():
            return

        loaded = 0
        for f in evo_dir.glob("*.json"):
            try:
                data = json.load(open(f))
                chain = data.get("chain", {})

                # Recursively process evolution chain.
                # "Recursive" = the function calls itself. Here it walks
                # one level down the family tree per call, and each level
                # tells its children who their parent is.
                # ("nonlocal loaded" just lets the inner function bump the
                # counter defined outside it.)
                def process_chain(pokemon_data, parent_id=None):
                    nonlocal loaded

                    poke_id = extract_id_from_url(pokemon_data.get("species", {}).get("url"))

                    # No parent means we're at the base of the family
                    # (Charmander) -- nothing evolves INTO it, so there's
                    # no pair to record yet.
                    if poke_id and parent_id:
                        trigger = pokemon_data.get("evolution_details", [{}])[0]
                        trigger_type = get_name_from_obj(trigger.get("trigger"))
                        trigger_item = get_name_from_obj(trigger.get("item"))
                        trigger_level = trigger.get("min_level")

                        self.cursor.execute(
                            """INSERT OR IGNORE INTO pokemon_evolutions
                               (evolves_from_id, evolves_to_id, trigger_type, trigger_item, trigger_level)
                               VALUES (?, ?, ?, ?, ?)""",
                            (parent_id, poke_id, trigger_type, trigger_item, trigger_level)
                        )
                        loaded += 1

                    # ...then do the same for everything this evolves into.
                    for child in pokemon_data.get("evolves_to", []):
                        process_chain(child, poke_id)

                process_chain(chain)  # kick it off at the top of the family

            except Exception as e:
                pass

        self.conn.commit()
        print(f"  ✓ Loaded {loaded} evolution records")

    def load_pokemon_forms(self):
        """
        Load alternate forms (Alola, Galar, Mega, Gmax, etc.) so they show
        up under their BASE species (e.g. Mega Charizard X should appear
        when looking at Charizard, dex #6) even though the form itself is
        stored as its own separate "pokemon" entry with its own id.
        """
        print("\nLoading Pokemon forms...")

        form_dir = DATA_DIR / "pokemon-form"
        pokemon_dir = DATA_DIR / "pokemon"
        if not form_dir.exists() or not pokemon_dir.exists():
            return

        loaded = 0
        for f in form_dir.glob("*.json"):
            try:
                data = json.load(open(f))

                form_id = data.get("id")
                variant_pokemon_id = extract_id_from_url(data.get("pokemon", {}).get("url"))
                form_name = data.get("name")
                is_mega = data.get("is_mega", False)
                order = data.get("order")

                types = data.get("types", [])
                type1 = get_name_from_obj(types[0].get("type")) if len(types) > 0 else None
                type2 = get_name_from_obj(types[1].get("type")) if len(types) > 1 else None

                if not (form_id and variant_pokemon_id):
                    continue

                # look up the variant's own pokemon file to find which base
                # species it belongs to, plus its height/weight. NOTE: the
                # is_default flag we actually want lives on the POKEMON
                # resource, not the pokemon-form resource -- pokemon-form's
                # is_default just means "the default form of THIS pokemon
                # id" which is trivially true almost always (even for Mega
                # Charizard X). pokemon.is_default is true only for the
                # plain/base pokemon of a species, which is what we want to
                # skip here (it's already shown as the main pokemon, not a
                # form of itself).
                variant_file = pokemon_dir / f"{variant_pokemon_id}.json"
                if not variant_file.exists():
                    continue

                variant_data = json.load(open(variant_file))
                if variant_data.get("is_default"):
                    continue

                base_pokemon_id = extract_id_from_url(variant_data.get("species", {}).get("url"))
                height = (variant_data.get("height") or 0) / 10
                weight = (variant_data.get("weight") or 0) / 10

                if not base_pokemon_id:
                    continue

                self.cursor.execute(
                    """INSERT OR IGNORE INTO pokemon_forms
                       (form_id, base_pokemon_id, variant_pokemon_id, form_name,
                        is_mega, type1, type2, height, weight, order_in_form)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (form_id, base_pokemon_id, variant_pokemon_id, form_name,
                     is_mega, type1, type2, height, weight, order)
                )
                loaded += 1

            except Exception as e:
                pass

        self.conn.commit()
        print(f"  ✓ Loaded {loaded} forms")

    def close(self):
        self.conn.close()

    def print_summary(self):
        """Print database summary."""
        # Just a sanity check at the end: count the rows in each table so
        # you can eyeball whether anything came out suspiciously empty.
        print("\n" + "="*50)
        print("DATABASE SUMMARY")
        print("="*50)

        tables = [
            "pokemon",
            "pokemon_battle_stats",
            "pokemon_biological",
            "pokemon_moves",
            "pokemon_tm_hm",
            "pokemon_abilities",
            "pokemon_egg_groups",
            "pokemon_descriptions",
            "pokemon_forms",
            "pokemon_evolutions",
            "type",
            "move",
            "ability"
        ]

        for table in tables:
            count = self.cursor.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            # The {table:.<40} bit pads the name out with dots so the
            # numbers line up in a neat column.
            print(f"  {table:.<40} {count:>6}")


# ============================================================
# RUN THE BUILD
# Everything above was definitions. This is the bit that actually happens
# when you run the file.
# ============================================================

# Clean up old database.
# .unlink() is pathlib's word for "delete this file". We always start from
# nothing so a rebuild can never leave stale rows behind.
if DB_PATH.exists():
    DB_PATH.unlink()

# Build database
db = PokedexDB(DB_PATH)

print("Building Pokedex Database")
print("="*50)

# ORDER MATTERS HERE. Reference data first (types/moves/games), because
# the pokemon rows point at it. Species after core, because it UPDATEs
# rows core created. Forms last, because they need the base pokemon to
# already exist.
db.create_tables()
db.load_reference_data()
db.load_pokemon_core()
db.load_pokemon_species()
db.load_pokemon_moves()
db.load_tm_hm()
db.load_evolutions()
db.load_pokemon_forms()

db.print_summary()
db.close()

print(f"\n✓ Database saved to {DB_PATH}")
