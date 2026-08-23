# Pokédex Project: Decisions & Progress

## COMPLETED
- DB: normalized schema, 23 tables, full PokeAPI parsing
- Backend: FastAPI, endpoints for pokemon/evolution/moves/abilities/type-chart/encounters
- Frontend: clean view (/) with full feature set
- Pokedex skin: /pokedex with Gen1 shell design
- Theme toggle: radio buttons, both views functional
- Moves: sorted by level, pre-evolution merges w/ sprite tags
- Evolution: full tree flow chart, branching support, current marked, methods on arrows
- Stat bars: value labels, crimson→yellow→green gradient
- Type chart: 18x18 matrix, color-coded cells
- Map system: Kanto only, generation-grouped locations, pin highlighting
- Sprites: carousel, shiny detection w/ rainbow stripes
- Descriptions: carousel by version
- Forms: clickable cards, variant switching
- **Shell layout overhaul**: reverse bevel top bar with editable pokemon name field, removed A/B buttons, redesigned D-pad on left with Genesis-style brown island housing
- **Egg group icons**: 15 SVG icons implemented (bug=ladybug, ditto=ditto sprite, dragon=skull, fairy=butterfly, flying=feather, humanshape=stick figure, indeterminate=!!, mineral=diamond, monster=mini Godzilla, no-eggs=egg with X, plant=leaf, water1/2/3=drops with numbers)
- **Habitat backgrounds**: 9 scenic SVG overlays (cave=dark water droplets, forest=trees+plants, grassland=field+sky+flowers, mountain=peaks, rare=vault+treasure, rough-terrain=wasteland, sea=Great Wave ripples, urban=buildings, waters-edge=beach split)
- **Type chart fix**: Axes swapped — defense types now column headers (top), move types now row labels (left) [modal currently pulled from Pokedex view, see PENDING]
- **Font audit**: Standardized to modern system font stack (system fonts first, then sans-serif fallbacks; monospace uses Menlo/Monaco/Courier)
- **Color icon**: Replaced drop shape with gradient circle (radial gradient: red→yellow→green→blue→purple)
- **Pokedex shell v2**: reverse bevel is a convex pill that bulges UP out of the top edge (opposite of an iPhone notch, not a cutout). Real tri-fold layout: `#pokedex-layout` has `perspective`, and the two side flip-panels use `rotateY` around their hinge edge (transform-origin at the inner edge) so they visibly angle *away* from the viewer like an open science-fair board — not just flat boxes in a row. Center panel wrapped in the same dark-red-bezel/light-screen treatment as the side panels so all three read as one hinged object. Layout: left flip panel (map) / center screen (sprite + pokedex entry side by side, type pills below, bio pills below that) / right flip panel (battle stats/moves/tm-hm/forms/evolution carousel). Type matchup chips + full type chart modal removed from the Pokedex view (still present on clean view "/") until there's a place for them in the new layout.
- **Region maps — ALL 9 REAL NOW**: user supplied reference images in `images for claude/` (Kanto/Johto/Hoenn/Sinnoh/Unova/Kalos = clean schematic diagrams; Paldea/Alola/Galar = photographic/illustrated in-game maps). Built `scripts/pixelate_map.py` (mode-color downsample for flat diagrams, HSV hue-bucket classification for the photographic ones) to trace each into pixel-art SVGs at `static/maps/{region}.svg`. `main.py` `REGIONS_WITH_REAL_MAPS` now includes all 9. Fixed two real bugs found along the way: (1) numpy 2.x scalar repr was leaking into SVG `fill="rgb(np.uint8(86)...)"` strings, silently rendering every generated map solid black — fixed in `grid_to_svg` by casting to plain `int`. (2) Let's Go Pikachu/Eevee share generation-number 7 with Sun/Moon/Ultra in the DB but are set in Kanto not Alola — was showing the Alola map for Let's Go's Kanto locations; now bucketed under a synthetic `LETS_GO_GEN_ID=700` → region "kanto" so it shows correctly as its own "Let's Go (Kanto)" tab.
- **Habitat backgrounds — pixel art**: rebuilt from checkerboard using the PC-box thumbnail strips in `images for claude/habitats.png` as style inspiration (forest bushes+sky, night city skyline, snow-capped peaks, beach, water waves — NOT the large tiled-pattern boxes below them, user explicitly disliked those). `scripts/build_habitats.py` generates all 9 as small pixel grids → SVG, embedded directly in `script.js`.

## EGG GROUP ICONS (compact, up to 3 colors each)
- bug: ladybug (red/black/orange)
- ditto: tiny ditto sprite
- dragon: dinosaur skull (bone/dark)
- fairy: butterfly (pink/purple/white)
- flying: feather (blue/white)
- humanshape: stick figure (brown/tan)
- indeterminate: "!!" (red/black)
- mineral: diamond (blue/white/silver)
- monster: mini Godzilla (green/dark)
- no-eggs: egg w/ green spots + red X
- plant: leaf (green/darker-green)
- water1/2/3: water drop w/ number inside (cyan/blue)

## HABITAT BACKGROUNDS (pixel-art scenes, small tiled SVG grid, repeats behind sprite)
- cave: dark navy, hanging stalactites, faint blue water-drip glints
- forest: pine tree silhouettes against sky blue, layered rows
- grassland: sky + green field band, clouds, scattered flowers
- mountain: gray snow-capped peaks against sky, tan foreground
- rare: vault door + scattered gold coins on dark brown
- rough-terrain: volcanic purple sky, cracked brown ground, lava vents
- sea: horizontal blue wave bands with light crest highlights
- urban: night skyline silhouette, lit yellow windows, purple-navy sky
- waters-edge: sand + water split, small palm-ish trees

## REGION MAPS (static/maps/{region}.svg, all pixel-art SVG)
- kanto: pre-existing hand-built map (build_kanto_map.py), untouched
- johto/hoenn/sinnoh/unova/kalos: mode-color downsample of the user's flat-diagram references, snapped to a curated palette (land/sea/road/city-red/town-blue/route-dot-green)
- paldea/alola/galar: HSV hue-bucket classification (ocean/lake/crater/sand/green/urban/snow etc per region) on the blurred source photo, then mode-downsampled — reads as clean pixel art instead of a blurry photo
- Kanto pins (data/maps/kanto_pins.json) are the only region with populated interactive pin coordinates; other 8 regions show the map image with the location-name list but no pin dots yet (pins.json files are empty `{}`) — future work if wanted

## PENDING / REMINDERS FROM USER (2026-08-11)
- **Habitat background reference images**: user has more specific reference art in mind beyond the box-thumbnail inspiration already used — may want another pass later.
- **Region map pin data**: only Kanto has real per-location pin coordinates. Populating the other 8 regions' `data/maps/{region}_pins.json` (matching PokeAPI location-area slugs to x/y% on the new maps) is unstarted.
- **Type matchup chart**: pulled out of the Pokedex view for now — find a place for it in the new 3-screen layout once the rest of the layout settles.
- Egg groups each get their own color palette
- All new assets should be simple, cute, compact pixel-friendly

## NOTES
- Name field in top bevel should show current pokemon, be editable (cosmetic? or save to somewhere?)
- D-pad is decorative only
- Habitats: scenery shouldn't obscure pokemon meaningfully, but overlap OK
- Map/habitat pixel-art generation scripts live in scripts/ (pixelate_map.py, build_habitats.py) — reusable if the user brings new reference images
