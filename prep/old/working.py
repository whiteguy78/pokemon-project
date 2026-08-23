"""
DEAD CODE. Kept for reference only -- nothing in the app uses this.

This was the first attempt at building the database, before the current
pipeline existed. It works, it's just a worse idea:

  - It hits the PokeAPI over the network for every single pokemon, every
    time you run it. About 1,300 requests, and if it dies halfway you
    start again. The current approach (prep/pokeapi_rip.py) downloads
    everything to disk once, so rebuilding the database afterwards is
    instant and offline.
  - It writes to Pokemon_data.db (also in this folder) with a different
    table layout to the real one.
  - It has no moves/evolution/type-chart handling at all.

The replacement is prep/pokeapi_rip.py + prep/build_pokedex_db.py, which
build data/pokemon.db -- the file the app actually reads.

Left in the repo because the schema sketch here (a "fact" table plus
narrow child tables) is what the current schema grew out of, and because
throwing away the first version of something is how you lose the thread of
why the second one looks the way it does.
"""
import os
import requests
import pandas as pd
import time
import sqlite3
import re

def create_pokemon_fact():
    """Build the master list: every pokemon and which species it belongs to.

    A "species" is Pikachu; the "varieties" are Pikachu, Cosplay Pikachu,
    Gigantamax Pikachu, etc. This walks every species and records all of
    its varieties as separate rows, which is why the row count comes out
    well above the ~1,025 you'd expect.
    """
    import sqlite3
    import requests
    import pandas as pd

    DB_NAME = "Pokemon_data.db"

    next_url = "https://pokeapi.co/api/v2/pokemon-species/"
    species_list = []

    while next_url:

        response = requests.get(next_url)
        if response.status_code != 200:
            print(
                f"Error getting species list: "
                f"{response.status_code}"
            )
            return None

        data = response.json()
        species_list.extend(data["results"])
        next_url = data["next"]

        print(f"Found {len(species_list)} species...")


    pokemon_list = []  
    # Get every variety belonging to every species


    for i, species in enumerate(species_list, start=1):

        response = requests.get(species["url"])
        if response.status_code != 200:
            print(
                f"Error getting {species['name']}: "
                f"{response.status_code}"
            )
            continue

        species_data = response.json()

        # This is the actual Pokedex/species number.
        pokedex_no = species_data["id"]

        # This is the base species name.
        species_name = species_data["name"]


        for variety in species_data["varieties"]:

            pokemon = variety["pokemon"]
            pokemon_id = int(pokemon["url"].rstrip("/").split("/")[-1])
            pokemon_name = pokemon["name"]
            is_default = int(variety["is_default"])
            pokemon_list.append((
                pokemon_id,
                pokemon_name,
                pokedex_no,
                species_name,
                is_default
            ))

        print(
            f"[{i}/{len(species_list)}] "
            f"{species_name}: "
            f"{len(species_data['varieties'])} varieties"
        )


    df = pd.DataFrame(
        pokemon_list,
        columns=[
            "id",
            "base_pokemon",
            "pokedex_no",
            "species_name",
            "is_default"
        ]
    )

    df.drop_duplicates(
        subset=["id"],
        inplace=True
    )

    df.sort_values(
        by="id",
        inplace=True
    )

    df.reset_index(
        drop=True,
        inplace=True
    )

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_fact (
            id INTEGER PRIMARY KEY,
            base_pokemon TEXT NOT NULL,
            pokedex_no INTEGER NOT NULL,
            species_name TEXT NOT NULL,
            is_default INTEGER NOT NULL
        )
    """)

     # truncate to overwrite/add new pokemon, dev artifact

    cursor.execute("DELETE FROM pokemon_fact")

    cursor.executemany("""
        INSERT INTO pokemon_fact
        (
            id,
            base_pokemon,
            pokedex_no,
            species_name,
            is_default
        )
        VALUES (?, ?, ?, ?, ?)
    """, df.itertuples(index=False, name=None))

    conn.commit()
    conn.close()

    print()
    print(f"Found {len(df)} total Pokemon varieties.")
    print(f"Saved {len(df)} rows to pokemon_fact.")

    return df



def load_pokemon_data(pokemon_id):
    """Fetch one pokemon from the API and write it into the child tables.

    Creates the tables if they don't exist yet (CREATE TABLE IF NOT
    EXISTS), then inserts. The DELETE-then-INSERT pattern further down is
    how it avoids leaving stale rows behind on a re-run -- see the comment
    where it starts.
    """

    DB_NAME = "Pokemon_data.db"

    # ---------------------------------------------------------
    # Get data from PokeAPI
    # ---------------------------------------------------------

    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"

    response = requests.get(url)

    if response.status_code != 200:
        print(f"Error getting Pokemon ID {pokemon_id}: "
              f"{response.status_code}")
        return

    data = response.json()

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # ---------------------------------------------------------
    # Create child tables
    # ---------------------------------------------------------

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_biometrics (
            pokemon_id INTEGER PRIMARY KEY,
            height INTEGER,
            weight INTEGER,
            base_experience INTEGER,

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_battle (
            pokemon_id INTEGER PRIMARY KEY,
            hp INTEGER,
            attack INTEGER,
            defense INTEGER,
            special_attack INTEGER,
            special_defense INTEGER,
            speed INTEGER,

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_abilities (
            pokemon_id INTEGER NOT NULL,
            ability_name TEXT NOT NULL,
            ability_url TEXT,
            slot INTEGER,
            is_hidden INTEGER,

            PRIMARY KEY (pokemon_id, ability_name),

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_types (
            pokemon_id INTEGER NOT NULL,
            type_name TEXT NOT NULL,
            type_url TEXT,
            slot INTEGER,

            PRIMARY KEY (pokemon_id, slot),

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_moves (
            pokemon_id INTEGER NOT NULL,
            move_name TEXT NOT NULL,
            move_url TEXT,
            version_group TEXT,
            learn_method TEXT,
            level_learned_at INTEGER,
            move_order INTEGER,

            PRIMARY KEY (
                pokemon_id,
                move_name,
                version_group,
                learn_method,
                level_learned_at
            ),

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            pokemon_id INTEGER NOT NULL,
            generation TEXT NOT NULL,
            data_type TEXT NOT NULL,
            slot INTEGER,
            value TEXT,

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pokemon_media (
            pokemon_id INTEGER PRIMARY KEY,

            front_default TEXT,
            front_shiny TEXT,
            front_female TEXT,
            front_shiny_female TEXT,

            back_default TEXT,
            back_shiny TEXT,
            back_female TEXT,
            back_shiny_female TEXT,

            official_artwork TEXT,
            official_artwork_shiny TEXT,

            dream_world TEXT,
            home TEXT,

            cry_latest TEXT,
            cry_legacy TEXT,

            FOREIGN KEY (pokemon_id)
                REFERENCES pokemon_fact(id)
        )
    """)

    cursor.execute("""
        INSERT OR REPLACE INTO pokemon_biometrics
        (
            pokemon_id,
            height,
            weight,
            base_experience
        )
        VALUES (?, ?, ?, ?)
    """, (
        data["id"],
        data["height"],
        data["weight"],
        data["base_experience"]
    ))

    stats = {}

    for stat in data["stats"]:
        stats[stat["stat"]["name"]] = stat["base_stat"]

    cursor.execute("""
        INSERT OR REPLACE INTO pokemon_battle
        (
            pokemon_id,
            hp,
            attack,
            defense,
            special_attack,
            special_defense,
            speed
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        stats.get("hp"),
        stats.get("attack"),
        stats.get("defense"),
        stats.get("special-attack"),
        stats.get("special-defense"),
        stats.get("speed")
    ))

# deleting the next few tables to clear out old values -- this is a long table with header/value pairs so 
# old values could remain if we just update. plus there's not a happy index on these so

    cursor.execute("""
        DELETE FROM pokemon_abilities
        WHERE pokemon_id = ?
    """, (data["id"],))


    for ability in data["abilities"]:

        cursor.execute("""
            INSERT INTO pokemon_abilities
            (
                pokemon_id,
                ability_name,
                ability_url,
                slot,
                is_hidden
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            data["id"],
            ability["ability"]["name"],
            ability["ability"]["url"],
            ability["slot"],
            int(ability["is_hidden"])
        ))


    cursor.execute("""
        DELETE FROM pokemon_types
        WHERE pokemon_id = ?
    """, (data["id"],))

    for pokemon_type in data["types"]:

        cursor.execute("""
            INSERT INTO pokemon_types
            (
                pokemon_id,
                type_name,
                type_url,
                slot
            )
            VALUES (?, ?, ?, ?)
        """, (
            data["id"],
            pokemon_type["type"]["name"],
            pokemon_type["type"]["url"],
            pokemon_type["slot"]
        ))


    cursor.execute("""
        DELETE FROM pokemon_moves
        WHERE pokemon_id = ?
    """, (data["id"],))

    for move in data["moves"]:

        move_name = move["move"]["name"]
        move_url = move["move"]["url"]

        for version_detail in move["version_group_details"]:

            version_group = (
                version_detail["version_group"]["name"]
            )

            learn_method = (
                version_detail["move_learn_method"]["name"]
            )

            level = version_detail["level_learned_at"]

            move_order = version_detail.get("order")

            cursor.execute("""
                INSERT INTO pokemon_moves
                (
                    pokemon_id,
                    move_name,
                    move_url,
                    version_group,
                    learn_method,
                    level_learned_at,
                    move_order
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data["id"],
                move_name,
                move_url,
                version_group,
                learn_method,
                level,
                move_order
            ))


    cursor.execute("""
        DELETE FROM pokemon_history
        WHERE pokemon_id = ?
    """, (data["id"],))

    # Past types

    for past_type in data.get("past_types", []):

        generation = past_type["generation"]["name"]

        for pokemon_type in past_type["types"]:

            cursor.execute("""
                INSERT INTO pokemon_history
                (
                    pokemon_id,
                    generation,
                    data_type,
                    slot,
                    value
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                data["id"],
                generation,
                "type",
                pokemon_type["slot"],
                pokemon_type["type"]["name"]
            ))



    for past_ability in data.get("past_abilities", []):

        generation = past_ability["generation"]["name"]

        for ability in past_ability["abilities"]:

            if ability["ability"] is not None:
                value = ability["ability"]["name"]
            else:
                value = None

            cursor.execute("""
                INSERT INTO pokemon_history
                (
                    pokemon_id,
                    generation,
                    data_type,
                    slot,
                    value
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                data["id"],
                generation,
                "ability",
                ability["slot"],
                value
            ))

 
    sprites = data["sprites"]

    official_artwork = (
        sprites.get("other", {})
        .get("official-artwork", {})
    )

    dream_world = (
        sprites.get("other", {})
        .get("dream-world", {})
    )

    home = (
        sprites.get("other", {})
        .get("home", {})
    )

    cries = data.get("cries", {})

    cursor.execute("""
        INSERT OR REPLACE INTO pokemon_media
        (
            pokemon_id,
            front_default,
            front_shiny,
            front_female,
            front_shiny_female,
            back_default,
            back_shiny,
            back_female,
            back_shiny_female,
            official_artwork,
            official_artwork_shiny,
            dream_world,
            home,
            cry_latest,
            cry_legacy
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        sprites.get("front_default"),
        sprites.get("front_shiny"),
        sprites.get("front_female"),
        sprites.get("front_shiny_female"),
        sprites.get("back_default"),
        sprites.get("back_shiny"),
        sprites.get("back_female"),
        sprites.get("back_shiny_female"),
        official_artwork.get("front_default"),
        official_artwork.get("front_shiny"),
        dream_world.get("front_default"),
        home.get("front_default"),
        cries.get("latest"),
        cries.get("legacy")
    ))

    conn.commit()
    conn.close()

    print(f"Loaded {data['name']} (ID {data['id']})")


def get_pokemon_data():
    """Run load_pokemon_data() for every pokemon in the fact table."""
    conn = sqlite3.connect("Pokemon_data.db")
    cursor = conn.cursor()

    # The "--limit 3" is commented out in SQL (-- starts a comment there,
    # same as # does in Python). Handy for testing on three rows.
    cursor.execute("select id from pokemon_fact --limit 3")
    loop_list = [row[0] for row in cursor.fetchall()]
    conn.close()

    for n in loop_list:
        load_pokemon_data(n)


# These two lines at the bottom are what actually ran. Step one built the
# master list; then you'd swap the comment to run step two.
print(create_pokemon_fact())
# get_pokemon_data()

