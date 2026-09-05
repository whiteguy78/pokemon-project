"""
All the database reading lives here.

main.py handles the web side of things (URLs in, JSON out). This file
handles the database side: every SQL query the app runs is one method on
the Pokedex class below. Keeping them apart means main.py never has SQL
scattered through it, and if the database schema ever changes, this is the
only file that has to change.

Nothing in here ever writes to the database -- the database is built once
by the scripts in prep/. This is read-only.

How you use it:

    db = Pokedex()               # open the database
    poke = db.get_full_pokemon(6)  # ask it something
    db.close()                   # close it again
"""
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional

# Where the database file is. Worked out from THIS file's location
# (pokedex_queries.py -> data/pokemon.db) so it doesn't
# matter which folder you launch the app from.
DB_PATH = Path(__file__).resolve().parent / "data" / "pokemon.db"


class Pokedex:
    def __init__(self, db_path=DB_PATH):
        # Open a connection to the SQLite file.
        self.conn = sqlite3.connect(db_path)
        # row_factory = sqlite3.Row means results come back so you can say
        # row['name'] instead of row[0]. Much easier to read.
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    # -----------------------------------------------------------------
    # SIMPLE ONE-TABLE LOOKUPS
    # Each of these is "find the row(s) for this pokemon in one table".
    # The "?" in the SQL is a placeholder -- SQLite fills it in with the
    # value in the tuple after it. Always do it this way rather than
    # gluing strings together; it's how you avoid SQL injection.
    # -----------------------------------------------------------------

    def get_pokemon_by_dex_number(self, dex_no: int) -> Optional[Dict]:
        """Get basic Pokemon info by National Dex number."""
        return self.cursor.execute(
            "SELECT * FROM pokemon WHERE national_dex_no = ?", (dex_no,)
        ).fetchone()

    def get_pokemon_by_name(self, name: str) -> Optional[Dict]:
        """Get basic Pokemon info by name."""
        return self.cursor.execute(
            "SELECT * FROM pokemon WHERE name LIKE ?", (f"%{name}%",)
        ).fetchone()

    def get_battle_stats(self, pokemon_id: int) -> Optional[Dict]:
        """Get stats and types for a Pokemon."""
        return self.cursor.execute(
            "SELECT * FROM pokemon_battle_stats WHERE pokemon_id = ?", (pokemon_id,)
        ).fetchone()

    def get_biological_data(self, pokemon_id: int) -> Optional[Dict]:
        """Get height, weight, color, habitat."""
        return self.cursor.execute(
            "SELECT * FROM pokemon_biological WHERE pokemon_id = ?", (pokemon_id,)
        ).fetchone()

    def get_abilities(self, pokemon_id: int) -> List[Dict]:
        """Get all abilities for a Pokemon."""
        return self.cursor.execute(
            """SELECT ability_name, slot, is_hidden
               FROM pokemon_abilities
               WHERE pokemon_id = ?
               ORDER BY slot""",
            (pokemon_id,)
        ).fetchall()

    def get_egg_groups(self, pokemon_id: int) -> List[str]:
        """Get egg groups for a Pokemon."""
        rows = self.cursor.execute(
            "SELECT egg_group_name FROM pokemon_egg_groups WHERE pokemon_id = ?",
            (pokemon_id,)
        ).fetchall()
        # The query gives back rows; we only want the one column out of each.
        return [row['egg_group_name'] for row in rows]

    def get_moves(self, pokemon_id: int) -> List[Dict]:
        """
        Get level-up/egg/tutor/etc moves for a Pokemon (NOT tm/hm moves --
        those live in get_tm_hm_moves() instead). Joins against the move
        table to bring in each move's type, for the colored type chip.
        Level-up moves come first, lowest level first (the order you'd
        actually learn them in-game); everything else (egg, tutor, ...)
        follows, grouped by method.
        """
        # The CASE WHEN in the ORDER BY is the "level-up moves first" bit:
        # it scores level-up moves 0 and everything else 1, then sorts on
        # that score before anything else.
        return self.cursor.execute(
            """SELECT pm.move_name, pm.level_learned, pm.learn_method, m.type AS move_type
               FROM pokemon_moves pm
               LEFT JOIN move m ON pm.move_name = m.name
               WHERE pm.pokemon_id = ? AND pm.learn_method != 'machine'
               ORDER BY CASE WHEN pm.learn_method = 'level-up' THEN 0 ELSE 1 END,
                        pm.level_learned ASC, pm.learn_method ASC, pm.move_name ASC""",
            (pokemon_id,)
        ).fetchall()

    def get_pre_evolution_ids(self, pokemon_id: int) -> List[int]:
        """
        Walk backward up the evolution chain: [immediate pre-evolution,
        its pre-evolution, ...] up to the base of the line. Empty list if
        this pokemon is already the base form.
        """
        # Keep asking "what does this evolve FROM?" until nothing comes
        # back, which means we've reached the bottom of the family.
        ancestors = []
        current_id = pokemon_id
        while True:
            row = self.cursor.execute(
                "SELECT evolves_from_id FROM pokemon_evolutions WHERE evolves_to_id = ?",
                (current_id,)
            ).fetchone()
            if row is None:
                break  # nothing evolves into this one -- we're at the base
            ancestors.append(row['evolves_from_id'])
            current_id = row['evolves_from_id']
        return ancestors

    def get_tm_hm_moves(self, pokemon_id: int) -> List[Dict]:
        """Get the TM/HM list for a Pokemon: which move, which type, which TM/HM number."""
        return self.cursor.execute(
            """SELECT DISTINCT move_name, move_type, tm_code
               FROM pokemon_tm_hm
               WHERE pokemon_id = ?
               ORDER BY tm_code""",
            (pokemon_id,)
        ).fetchall()

    def get_descriptions(self, pokemon_id: int, language='en') -> List[Dict]:
        """
        Get descriptions for a Pokemon across all versions, ordered by when
        that game actually released (oldest first) rather than alphabetically.
        """
        # sort_order comes from the version table, which prep/ filled in
        # from PokeAPI's release-order field. Without the join we'd get
        # Blue, Crystal, Diamond... which is meaningless.
        return self.cursor.execute(
            """SELECT pd.version, pd.text
               FROM pokemon_descriptions pd
               LEFT JOIN version v ON pd.version = v.name
               WHERE pd.pokemon_id = ? AND pd.language = ?
               ORDER BY v.sort_order""",
            (pokemon_id, language)
        ).fetchall()

    def get_description(self, pokemon_id: int, version: str = None, language: str = 'en') -> Optional[str]:
        """
        Get a single description for a Pokemon.
        If version not specified, returns the first one found.
        """
        if version:
            row = self.cursor.execute(
                """SELECT text FROM pokemon_descriptions
                   WHERE pokemon_id = ? AND language = ? AND version = ?""",
                (pokemon_id, language, version)
            ).fetchone()
        else:
            row = self.cursor.execute(
                """SELECT text FROM pokemon_descriptions
                   WHERE pokemon_id = ? AND language = ?
                   LIMIT 1""",
                (pokemon_id, language)
            ).fetchone()

        return row['text'] if row else None

    # -----------------------------------------------------------------
    # EVOLUTION
    # -----------------------------------------------------------------

    def get_evolution_chain(self, pokemon_id: int) -> Dict:
        """
        Get Pokemon that this one evolves from and to.
        Returns: {evolves_from: [...], evolves_to: [...]}
        """
        # Just the immediate neighbours -- one step back and one step
        # forward. get_full_evolution_tree() below is what the app
        # actually uses; this is the simpler version.
        evolves_from = self.cursor.execute(
            """SELECT p.id, p.name, p.national_dex_no, pe.trigger_type, pe.trigger_level, pe.trigger_item
               FROM pokemon_evolutions pe
               JOIN pokemon p ON pe.evolves_from_id = p.id
               WHERE pe.evolves_to_id = ?""",
            (pokemon_id,)
        ).fetchall()

        evolves_to = self.cursor.execute(
            """SELECT p.id, p.name, p.national_dex_no, pe.trigger_type, pe.trigger_level, pe.trigger_item
               FROM pokemon_evolutions pe
               JOIN pokemon p ON pe.evolves_to_id = p.id
               WHERE pe.evolves_from_id = ?""",
            (pokemon_id,)
        ).fetchall()

        return {
            'evolves_from': [dict(row) for row in evolves_from],
            'evolves_to': [dict(row) for row in evolves_to]
        }

    def get_full_evolution_tree(self, pokemon_id: int) -> Dict:
        """
        Get the WHOLE evolution line as a tree, starting from the base of
        the chain (not just this pokemon's immediate neighbors). Handles
        branches (Eevee, Tyrogue, Wurmple, ...) naturally -- a branch point
        just has more than one child.

        Returns a nested dict:
        {id, name, national_dex_no, trigger: {...} | None, children: [...]}
        "trigger" describes how you get FROM the parent INTO this node
        (None for the root, since it has no parent).
        """
        # Step 1: climb to the very bottom of the family. If you asked for
        # Charizard, we want to start drawing from Charmander.
        root_id = pokemon_id
        while True:
            row = self.cursor.execute(
                "SELECT evolves_from_id FROM pokemon_evolutions WHERE evolves_to_id = ?",
                (root_id,)
            ).fetchone()
            if row is None:
                break
            root_id = row['evolves_from_id']

        # Step 2: from there, build the tree downward. build_node() calls
        # itself once for each thing this pokemon evolves into, and those
        # calls do the same again, until it runs out of evolutions.
        def build_node(node_id, trigger):
            info = self.cursor.execute(
                "SELECT id, name, national_dex_no FROM pokemon WHERE id = ?", (node_id,)
            ).fetchone()
            child_edges = self.cursor.execute(
                """SELECT evolves_to_id, trigger_type, trigger_level, trigger_item
                   FROM pokemon_evolutions WHERE evolves_from_id = ?""",
                (node_id,)
            ).fetchall()

            return {
                'id': info['id'],
                'name': info['name'],
                'national_dex_no': info['national_dex_no'],
                'trigger': trigger,
                'children': [
                    build_node(edge['evolves_to_id'], {
                        'trigger_type': edge['trigger_type'],
                        'trigger_level': edge['trigger_level'],
                        'trigger_item': edge['trigger_item'],
                    })
                    for edge in child_edges
                ],
            }

        return build_node(root_id, None)

    # -----------------------------------------------------------------
    # ALTERNATE FORMS (Mega / Gmax / regional)
    # -----------------------------------------------------------------

    def get_forms(self, pokemon_id: int) -> List[Dict]:
        """
        Get alternate forms for a Pokemon (Mega, Gmax, regional variants).
        pokemon_id here is the BASE species id (e.g. 6 for charizard).
        Each row includes the variant's own pokemon id (for loading its
        sprite/stats) and its own type(s).
        """
        return self.cursor.execute(
            """SELECT form_id, variant_pokemon_id, form_name, is_mega,
                      type1, type2, height, weight
               FROM pokemon_forms
               WHERE base_pokemon_id = ?
               ORDER BY order_in_form""",
            (pokemon_id,)
        ).fetchall()

    def get_variant(self, variant_pokemon_id: int) -> Optional[Dict]:
        """
        Get display data for one alternate form (Mega/Gmax/regional), keyed
        by its OWN pokemon id -- not a dex number, since these don't have
        national dex numbers of their own. Used when a user clicks a form
        in the Forms tab.
        """
        stats = self.get_battle_stats(variant_pokemon_id)
        if not stats:
            return None  # no such form

        name_row = self.cursor.execute(
            "SELECT name FROM pokemon WHERE id = ?", (variant_pokemon_id,)
        ).fetchone()

        return {
            'id': variant_pokemon_id,
            'name': name_row['name'] if name_row else None,
            'stats': dict(stats),
            'biological': dict(self.get_biological_data(variant_pokemon_id)),
            'abilities': [dict(a) for a in self.get_abilities(variant_pokemon_id)],
        }

    # -----------------------------------------------------------------
    # THE BIG ONE
    # -----------------------------------------------------------------

    def get_full_pokemon(self, dex_no: int) -> Dict:
        """
        Get ALL data for a Pokemon by dex number.
        Returns a dictionary with everything.
        """
        # This is just every method above, called in a row and packed into
        # one dictionary. main.py calls this once per page load.
        poke = self.get_pokemon_by_dex_number(dex_no)
        if not poke:
            return None  # no pokemon with that number

        # Careful: dex number and internal id are NOT the same thing for
        # alternate forms, so everything below is keyed on the id.
        pokemon_id = poke['id']

        return {
            'id': pokemon_id,
            'name': poke['name'],
            'national_dex_no': poke['national_dex_no'],
            'generation_id': poke['generation_id'],
            'stats': dict(self.get_battle_stats(pokemon_id)),
            'biological': dict(self.get_biological_data(pokemon_id)),
            'abilities': [dict(a) for a in self.get_abilities(pokemon_id)],
            'egg_groups': self.get_egg_groups(pokemon_id),
            'moves': [dict(m) for m in self.get_moves(pokemon_id)],
            'tm_hm_moves': [dict(m) for m in self.get_tm_hm_moves(pokemon_id)],
            'descriptions': [dict(d) for d in self.get_descriptions(pokemon_id)],
            'evolution': self.get_full_evolution_tree(pokemon_id),
            'forms': [dict(f) for f in self.get_forms(pokemon_id)],
        }

    # -----------------------------------------------------------------
    # SEARCH + DETAIL POPUPS
    # -----------------------------------------------------------------

    def search_pokemon(self, query: str, limit: int = 8) -> List[Dict]:
        """Search for Pokemon by partial name OR dex number, for typeahead dropdowns."""
        query = query.strip()
        if query.isdigit():
            # They typed a number. Show the exact dex match first, then
            # anything whose NAME happens to contain those digits.
            # ("national_dex_no != ?" sorts False(0) before True(1), which
            # puts the exact match at the top.)
            rows = self.cursor.execute(
                """SELECT id, name, national_dex_no FROM pokemon
                   WHERE national_dex_no IS NOT NULL
                     AND (national_dex_no = ? OR name LIKE ?)
                   ORDER BY (national_dex_no != ?), national_dex_no
                   LIMIT ?""",
                (int(query), f"%{query}%", int(query), limit)
            ).fetchall()
        else:
            # They typed letters. Plain "name contains this" search.
            # national_dex_no IS NOT NULL filters out alternate forms,
            # which don't have dex numbers and shouldn't clutter the list.
            rows = self.cursor.execute(
                """SELECT id, name, national_dex_no FROM pokemon
                   WHERE name LIKE ? AND national_dex_no IS NOT NULL
                   ORDER BY national_dex_no
                   LIMIT ?""",
                (f"%{query}%", limit)
            ).fetchall()
        return [dict(row) for row in rows]

    def get_move_detail(self, move_name: str) -> Optional[Dict]:
        """Get a move's flavor text + stats, for the click-to-see-detail panel."""
        row = self.cursor.execute(
            "SELECT name, type, power, accuracy, pp, damage_class, short_effect, flavor_text FROM move WHERE name = ?",
            (move_name,)
        ).fetchone()
        return dict(row) if row else None

    def get_ability_detail(self, ability_name: str) -> Optional[Dict]:
        """Get an ability's flavor text, for the click-to-see-detail panel."""
        row = self.cursor.execute(
            "SELECT name, short_effect FROM ability WHERE name = ?",
            (ability_name,)
        ).fetchone()
        return dict(row) if row else None

    def get_type_chart(self) -> Dict:
        """
        Get the full attack-type x defend-type effectiveness matrix.
        Returns {"types": [...18 names], "matchup": {attacking: {defending: multiplier}}}
        """
        # The database stores this one row at a time ("fire beats grass,
        # 2x"). The frontend wants it as a nested lookup, so we reshape it
        # here: matchup["fire"]["grass"] == 2.0
        rows = self.cursor.execute(
            "SELECT attacking_type, defending_type, multiplier FROM type_matchup"
        ).fetchall()

        matchup = {}
        types_seen = []
        for row in rows:
            atk, dfn, mult = row['attacking_type'], row['defending_type'], row['multiplier']
            if atk not in matchup:
                matchup[atk] = {}
                types_seen.append(atk)  # keeps the 18 types in a stable order
            matchup[atk][dfn] = mult

        return {"types": types_seen, "matchup": matchup}

    def close(self):
        # Always call this when you're done -- it releases the file.
        self.conn.close()
