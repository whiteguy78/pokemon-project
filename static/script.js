// ===============================================================
// The entire front end. One file, no frameworks, no build step.
//
// Both pages use this same file:
//   index.html   -> the plain "clean" view
//   pokedex.html -> the same content wrapped in handheld-Pokedex chrome
// So a fair bit of the code below checks which theme is showing, or
// checks whether an element exists before touching it, because some parts
// of the page only exist in one of the two layouts.
//
// The shape of the whole thing, top to bottom:
//   1. Lookup tables (type colours, game colours)
//   2. Hand-drawn artwork, written out as SVG text (habitats, icons).
//      This is most of the file's length and none of its complexity --
//      scroll past it.
//   3. Grab every element from the page we'll want to update
//   4. State: which pokemon, which sprite, which slide we're on
//   5. loadPokemon() -- fetch from the server, then render everything
//   6. Event listeners, wiring the buttons up
//
// Where the data comes from: every fetch("/api/...") call below talks to
// the Python server in app/main.py. The browser stores nothing itself.
// ===============================================================

// ---------------------------------------------------------------
// COLOR LOOKUPS
// The colour for each pokemon type. Used for the type pills, the move
// chips, and the accent colour of the whole page (which follows whatever
// the current pokemon's first type is).
// ---------------------------------------------------------------
const TYPE_COLORS = {
    "Normal": "#8f8f6c", "Fire": "#e0651b", "Water": "#3e64c7",
    "Electric": "#b8960e", "Grass": "#4c9a2a", "Ice": "#4fadad",
    "Fighting": "#c03028", "Poison": "#a040a0", "Ground": "#b89241",
    "Flying": "#7a5fd1", "Psychic": "#d6386a", "Bug": "#7c8b12",
    "Rock": "#8c7a21", "Ghost": "#705898", "Dragon": "#5b2ad1",
    "Dark": "#705848", "Steel": "#7e7e99", "Fairy": "#d46a85",
};
const DEFAULT_COLOR = "#2b2f77";  // fallback if a type name doesn't match

// A colour per game, so the pokedex-entry banner is tinted by which game
// the entry came from (Red is red, Leafgreen is green, and so on).
const VERSION_COLORS = {
    "Red": "#c0392b", "Blue": "#2980b9", "Yellow": "#f1c40f", "Green": "#27ae60",
    "Gold": "#d4a017", "Silver": "#95a5a6", "Crystal": "#48c9b0",
    "Ruby": "#a93226", "Sapphire": "#1f618d", "Emerald": "#229954",
    "Firered": "#e67e22", "Leafgreen": "#52be80",
    "Diamond": "#7fb3d5", "Pearl": "#f1948a", "Platinum": "#839192",
    "Heartgold": "#d4ac0d", "Soulsilver": "#aab7b8",
    "Black": "#2c2c2c", "White": "#7f8c8d", "Black 2": "#1c1c1c", "White 2": "#979a9a",
    "X": "#3498db", "Y": "#e74c3c",
    "Omega Ruby": "#922b21", "Alpha Sapphire": "#1a5276",
    "Sun": "#f39c12", "Moon": "#34495e", "Ultra Sun": "#ca6f1e", "Ultra Moon": "#2e4053",
    "Lets Go Pikachu": "#f4d03f", "Lets Go Eevee": "#ba7048",
    "Sword": "#17a589", "Shield": "#884ea0",
    "Brilliant Diamond": "#5dade2", "Shining Pearl": "#f1948a",
    "Legends Arceus": "#ab8a5d", "Scarlet": "#c0392b", "Violet": "#8e44ad",
    "Colosseum": "#566573", "Xd": "#566573",
};

// Wraps a chunk of SVG text so CSS can use it as a background image,
// without it ever needing to be a separate file on disk. encodeURIComponent
// escapes the characters (#, <, spaces) that would otherwise break the URL.
function svgDataUri(svg) {
    return `url("data:image/svg+xml;utf8,${encodeURIComponent(svg)}")`;
}

// ---------------------------------------------------------------
// HABITAT BACKGROUNDS (pixel-art scenes, inspired by the PC-box
// thumbnail strips the user provided in "images for claude/habitats.png":
// forest bushes+sky, night city skyline, snow-capped peaks, beach,
// water waves. Built as small pixel grids, same style as the region maps.
//
// These nine functions are just long lists of coloured rectangles. They
// were GENERATED, not typed -- see prep/build_habitats.py, which draws
// them and prints the SVG. Don't hand-edit them; change that script and
// paste the new output in.
// ---------------------------------------------------------------
function habitatCave() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="5" width="15" height="5" fill="rgb(26, 24, 40)"/>
<rect x="15" y="5" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="20" y="5" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="40" y="5" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="45" y="5" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="65" y="5" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="70" y="5" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="90" y="5" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="95" y="5" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="105" y="5" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="110" y="5" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="10" width="15" height="5" fill="rgb(26, 24, 40)"/>
<rect x="15" y="10" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="20" y="10" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="40" y="10" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="45" y="10" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="65" y="10" width="5" height="5" fill="rgb(70, 110, 160)"/>
<rect x="70" y="10" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="90" y="10" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="95" y="10" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="105" y="10" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="110" y="10" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="15" width="15" height="5" fill="rgb(26, 24, 40)"/>
<rect x="15" y="15" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="20" y="15" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="40" y="15" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="45" y="15" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="65" y="15" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="70" y="15" width="20" height="5" fill="rgb(26, 24, 40)"/>
<rect x="90" y="15" width="5" height="5" fill="rgb(44, 40, 64)"/>
<rect x="95" y="15" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="105" y="15" width="5" height="5" fill="rgb(70, 110, 160)"/>
<rect x="110" y="15" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="20" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="10" y="20" width="15" height="5" fill="rgb(44, 40, 64)"/>
<rect x="25" y="20" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="35" y="20" width="15" height="5" fill="rgb(44, 40, 64)"/>
<rect x="50" y="20" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="60" y="20" width="15" height="5" fill="rgb(44, 40, 64)"/>
<rect x="75" y="20" width="10" height="5" fill="rgb(26, 24, 40)"/>
<rect x="85" y="20" width="30" height="5" fill="rgb(44, 40, 64)"/>
<rect x="115" y="20" width="5" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="25" width="120" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="30" width="120" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="35" width="40" height="5" fill="rgb(26, 24, 40)"/>
<rect x="40" y="35" width="5" height="5" fill="rgb(70, 110, 160)"/>
<rect x="45" y="35" width="35" height="5" fill="rgb(26, 24, 40)"/>
<rect x="80" y="35" width="5" height="5" fill="rgb(70, 110, 160)"/>
<rect x="85" y="35" width="35" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="40" width="120" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="45" width="120" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="50" width="80" height="5" fill="rgb(26, 24, 40)"/>
<rect x="80" y="50" width="5" height="5" fill="rgb(70, 110, 160)"/>
<rect x="85" y="50" width="35" height="5" fill="rgb(26, 24, 40)"/>
<rect x="0" y="55" width="15" height="5" fill="rgb(20, 18, 32)"/>
<rect x="15" y="55" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="20" y="55" width="15" height="5" fill="rgb(20, 18, 32)"/>
<rect x="35" y="55" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="40" y="55" width="80" height="5" fill="rgb(20, 18, 32)"/>
<rect x="0" y="60" width="20" height="5" fill="rgb(20, 18, 32)"/>
<rect x="20" y="60" width="10" height="5" fill="rgb(60, 56, 84)"/>
<rect x="30" y="60" width="90" height="5" fill="rgb(20, 18, 32)"/>
<rect x="0" y="65" width="10" height="5" fill="rgb(60, 56, 84)"/>
<rect x="10" y="65" width="65" height="5" fill="rgb(20, 18, 32)"/>
<rect x="75" y="65" width="10" height="5" fill="rgb(60, 56, 84)"/>
<rect x="85" y="65" width="5" height="5" fill="rgb(20, 18, 32)"/>
<rect x="90" y="65" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="95" y="65" width="25" height="5" fill="rgb(20, 18, 32)"/>
<rect x="0" y="70" width="40" height="5" fill="rgb(20, 18, 32)"/>
<rect x="40" y="70" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="45" y="70" width="15" height="5" fill="rgb(20, 18, 32)"/>
<rect x="60" y="70" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="65" y="70" width="5" height="5" fill="rgb(20, 18, 32)"/>
<rect x="70" y="70" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="75" y="70" width="5" height="5" fill="rgb(20, 18, 32)"/>
<rect x="80" y="70" width="10" height="5" fill="rgb(60, 56, 84)"/>
<rect x="90" y="70" width="15" height="5" fill="rgb(20, 18, 32)"/>
<rect x="105" y="70" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="110" y="70" width="10" height="5" fill="rgb(20, 18, 32)"/>
<rect x="0" y="75" width="5" height="5" fill="rgb(20, 18, 32)"/>
<rect x="5" y="75" width="10" height="5" fill="rgb(60, 56, 84)"/>
<rect x="15" y="75" width="35" height="5" fill="rgb(20, 18, 32)"/>
<rect x="50" y="75" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="55" y="75" width="15" height="5" fill="rgb(20, 18, 32)"/>
<rect x="70" y="75" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="75" y="75" width="30" height="5" fill="rgb(20, 18, 32)"/>
<rect x="105" y="75" width="5" height="5" fill="rgb(60, 56, 84)"/>
<rect x="110" y="75" width="10" height="5" fill="rgb(20, 18, 32)"/>
</svg>`);
}

function habitatForest() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="10" width="120" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="15" width="120" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="20" width="30" height="5" fill="rgb(150, 205, 225)"/>
<rect x="30" y="20" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="35" y="20" width="35" height="5" fill="rgb(150, 205, 225)"/>
<rect x="70" y="20" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="75" y="20" width="30" height="5" fill="rgb(150, 205, 225)"/>
<rect x="105" y="20" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="110" y="20" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="25" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="10" y="25" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="15" y="25" width="15" height="5" fill="rgb(150, 205, 225)"/>
<rect x="30" y="25" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="35" y="25" width="15" height="5" fill="rgb(150, 205, 225)"/>
<rect x="50" y="25" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="55" y="25" width="15" height="5" fill="rgb(150, 205, 225)"/>
<rect x="70" y="25" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="75" y="25" width="15" height="5" fill="rgb(150, 205, 225)"/>
<rect x="90" y="25" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="95" y="25" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="105" y="25" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="110" y="25" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="30" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="10" y="30" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="15" y="30" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="25" y="30" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="40" y="30" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="50" y="30" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="55" y="30" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="65" y="30" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="80" y="30" width="10" height="5" fill="rgb(150, 205, 225)"/>
<rect x="90" y="30" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="95" y="30" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="100" y="30" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="115" y="30" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="35" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="5" y="35" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="20" y="35" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="25" y="35" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="40" y="35" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="45" y="35" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="60" y="35" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="65" y="35" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="80" y="35" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="85" y="35" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="100" y="35" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="105" y="35" width="10" height="5" fill="rgb(34, 82, 30)"/>
<rect x="115" y="35" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="40" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="5" y="40" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="20" y="40" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="25" y="40" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="40" y="40" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="45" y="40" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="60" y="40" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="65" y="40" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="80" y="40" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="85" y="40" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="100" y="40" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="105" y="40" width="10" height="5" fill="rgb(34, 82, 30)"/>
<rect x="115" y="40" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="0" y="45" width="5" height="5" fill="rgb(150, 205, 225)"/>
<rect x="5" y="45" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="20" y="45" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="25" y="45" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="40" y="45" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="45" y="45" width="35" height="5" fill="rgb(34, 82, 30)"/>
<rect x="80" y="45" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="85" y="45" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="100" y="45" width="5" height="5" fill="rgb(46, 120, 40)"/>
<rect x="105" y="45" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="0" y="50" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="15" y="50" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="30" y="50" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="35" y="50" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="50" y="50" width="25" height="5" fill="rgb(34, 82, 30)"/>
<rect x="75" y="50" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="90" y="50" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="95" y="50" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="110" y="50" width="10" height="5" fill="rgb(34, 82, 30)"/>
<rect x="0" y="55" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="15" y="55" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="30" y="55" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="35" y="55" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="50" y="55" width="25" height="5" fill="rgb(34, 82, 30)"/>
<rect x="75" y="55" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="90" y="55" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="95" y="55" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="110" y="55" width="10" height="5" fill="rgb(34, 82, 30)"/>
<rect x="0" y="60" width="15" height="5" fill="rgb(34, 82, 30)"/>
<rect x="15" y="60" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="30" y="60" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="35" y="60" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="50" y="60" width="25" height="5" fill="rgb(34, 82, 30)"/>
<rect x="75" y="60" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="90" y="60" width="5" height="5" fill="rgb(34, 82, 30)"/>
<rect x="95" y="60" width="15" height="5" fill="rgb(46, 120, 40)"/>
<rect x="110" y="60" width="10" height="5" fill="rgb(34, 82, 30)"/>
<rect x="0" y="65" width="10" height="5" fill="rgb(58, 110, 46)"/>
<rect x="10" y="65" width="45" height="5" fill="rgb(46, 120, 40)"/>
<rect x="55" y="65" width="15" height="5" fill="rgb(58, 110, 46)"/>
<rect x="70" y="65" width="45" height="5" fill="rgb(46, 120, 40)"/>
<rect x="115" y="65" width="5" height="5" fill="rgb(58, 110, 46)"/>
<rect x="0" y="70" width="120" height="5" fill="rgb(44, 96, 36)"/>
<rect x="0" y="75" width="120" height="5" fill="rgb(44, 96, 36)"/>
</svg>`);
}

function habitatGrassland() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="10" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="15" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="20" width="75" height="5" fill="rgb(135, 206, 235)"/>
<rect x="75" y="20" width="20" height="5" fill="rgb(255, 255, 255)"/>
<rect x="95" y="20" width="25" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="25" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="30" width="25" height="5" fill="rgb(135, 206, 235)"/>
<rect x="25" y="30" width="15" height="5" fill="rgb(255, 255, 255)"/>
<rect x="40" y="30" width="80" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="35" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="40" width="120" height="5" fill="rgb(135, 206, 235)"/>
<rect x="0" y="45" width="120" height="5" fill="rgb(140, 205, 100)"/>
<rect x="0" y="50" width="120" height="5" fill="rgb(140, 205, 100)"/>
<rect x="0" y="55" width="15" height="5" fill="rgb(140, 205, 100)"/>
<rect x="15" y="55" width="5" height="5" fill="rgb(255, 210, 90)"/>
<rect x="20" y="55" width="100" height="5" fill="rgb(140, 205, 100)"/>
<rect x="0" y="60" width="85" height="5" fill="rgb(120, 190, 84)"/>
<rect x="85" y="60" width="5" height="5" fill="rgb(255, 210, 90)"/>
<rect x="90" y="60" width="30" height="5" fill="rgb(120, 190, 84)"/>
<rect x="0" y="65" width="45" height="5" fill="rgb(120, 190, 84)"/>
<rect x="45" y="65" width="5" height="5" fill="rgb(255, 140, 170)"/>
<rect x="50" y="65" width="70" height="5" fill="rgb(120, 190, 84)"/>
<rect x="0" y="70" width="100" height="5" fill="rgb(120, 190, 84)"/>
<rect x="100" y="70" width="5" height="5" fill="rgb(255, 140, 170)"/>
<rect x="105" y="70" width="15" height="5" fill="rgb(120, 190, 84)"/>
<rect x="0" y="75" width="120" height="5" fill="rgb(120, 190, 84)"/>
</svg>`);
}

function habitatMountain() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="10" width="120" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="15" width="120" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="20" width="30" height="5" fill="rgb(150, 205, 232)"/>
<rect x="30" y="20" width="5" height="5" fill="rgb(120, 128, 140)"/>
<rect x="35" y="20" width="25" height="5" fill="rgb(150, 205, 232)"/>
<rect x="60" y="20" width="5" height="5" fill="rgb(140, 148, 160)"/>
<rect x="65" y="20" width="55" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="25" width="25" height="5" fill="rgb(150, 205, 232)"/>
<rect x="25" y="25" width="15" height="5" fill="rgb(120, 128, 140)"/>
<rect x="40" y="25" width="15" height="5" fill="rgb(150, 205, 232)"/>
<rect x="55" y="25" width="15" height="5" fill="rgb(140, 148, 160)"/>
<rect x="70" y="25" width="50" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="30" width="20" height="5" fill="rgb(150, 205, 232)"/>
<rect x="20" y="30" width="25" height="5" fill="rgb(120, 128, 140)"/>
<rect x="45" y="30" width="10" height="5" fill="rgb(150, 205, 232)"/>
<rect x="55" y="30" width="15" height="5" fill="rgb(140, 148, 160)"/>
<rect x="70" y="30" width="15" height="5" fill="rgb(150, 205, 232)"/>
<rect x="85" y="30" width="5" height="5" fill="rgb(104, 112, 126)"/>
<rect x="90" y="30" width="30" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="35" width="20" height="5" fill="rgb(150, 205, 232)"/>
<rect x="20" y="35" width="25" height="5" fill="rgb(120, 128, 140)"/>
<rect x="45" y="35" width="5" height="5" fill="rgb(150, 205, 232)"/>
<rect x="50" y="35" width="25" height="5" fill="rgb(140, 148, 160)"/>
<rect x="75" y="35" width="5" height="5" fill="rgb(150, 205, 232)"/>
<rect x="80" y="35" width="15" height="5" fill="rgb(104, 112, 126)"/>
<rect x="95" y="35" width="25" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="40" width="15" height="5" fill="rgb(150, 205, 232)"/>
<rect x="15" y="40" width="30" height="5" fill="rgb(120, 128, 140)"/>
<rect x="45" y="40" width="35" height="5" fill="rgb(140, 148, 160)"/>
<rect x="80" y="40" width="20" height="5" fill="rgb(104, 112, 126)"/>
<rect x="100" y="40" width="20" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="45" width="10" height="5" fill="rgb(150, 205, 232)"/>
<rect x="10" y="45" width="35" height="5" fill="rgb(120, 128, 140)"/>
<rect x="45" y="45" width="35" height="5" fill="rgb(140, 148, 160)"/>
<rect x="80" y="45" width="25" height="5" fill="rgb(104, 112, 126)"/>
<rect x="105" y="45" width="15" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="50" width="10" height="5" fill="rgb(150, 205, 232)"/>
<rect x="10" y="50" width="20" height="5" fill="rgb(120, 128, 140)"/>
<rect x="30" y="50" width="5" height="5" fill="rgb(255, 255, 255)"/>
<rect x="35" y="50" width="5" height="5" fill="rgb(120, 128, 140)"/>
<rect x="40" y="50" width="45" height="5" fill="rgb(140, 148, 160)"/>
<rect x="85" y="50" width="20" height="5" fill="rgb(104, 112, 126)"/>
<rect x="105" y="50" width="15" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="55" width="5" height="5" fill="rgb(150, 205, 232)"/>
<rect x="5" y="55" width="20" height="5" fill="rgb(120, 128, 140)"/>
<rect x="25" y="55" width="15" height="5" fill="rgb(255, 255, 255)"/>
<rect x="40" y="55" width="20" height="5" fill="rgb(140, 148, 160)"/>
<rect x="60" y="55" width="5" height="5" fill="rgb(255, 255, 255)"/>
<rect x="65" y="55" width="20" height="5" fill="rgb(140, 148, 160)"/>
<rect x="85" y="55" width="5" height="5" fill="rgb(255, 255, 255)"/>
<rect x="90" y="55" width="20" height="5" fill="rgb(104, 112, 126)"/>
<rect x="110" y="55" width="10" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="60" width="20" height="5" fill="rgb(120, 128, 140)"/>
<rect x="20" y="60" width="25" height="5" fill="rgb(255, 255, 255)"/>
<rect x="45" y="60" width="10" height="5" fill="rgb(140, 148, 160)"/>
<rect x="55" y="60" width="15" height="5" fill="rgb(255, 255, 255)"/>
<rect x="70" y="60" width="10" height="5" fill="rgb(140, 148, 160)"/>
<rect x="80" y="60" width="15" height="5" fill="rgb(255, 255, 255)"/>
<rect x="95" y="60" width="20" height="5" fill="rgb(104, 112, 126)"/>
<rect x="115" y="60" width="5" height="5" fill="rgb(150, 205, 232)"/>
<rect x="0" y="65" width="30" height="5" fill="rgb(150, 205, 232)"/>
<rect x="30" y="65" width="25" height="5" fill="rgb(140, 148, 160)"/>
<rect x="55" y="65" width="15" height="5" fill="rgb(255, 255, 255)"/>
<rect x="70" y="65" width="5" height="5" fill="rgb(140, 148, 160)"/>
<rect x="75" y="65" width="25" height="5" fill="rgb(255, 255, 255)"/>
<rect x="100" y="65" width="20" height="5" fill="rgb(104, 112, 126)"/>
<rect x="0" y="70" width="120" height="5" fill="rgb(168, 176, 150)"/>
<rect x="0" y="75" width="120" height="5" fill="rgb(168, 176, 150)"/>
</svg>`);
}

function habitatRare() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="10" width="120" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="15" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="15" width="30" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="15" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="20" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="20" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="20" width="20" height="5" fill="rgb(74, 56, 38)"/>
<rect x="70" y="20" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="20" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="25" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="25" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="25" width="10" height="5" fill="rgb(74, 56, 38)"/>
<rect x="60" y="25" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="65" y="25" width="5" height="5" fill="rgb(74, 56, 38)"/>
<rect x="70" y="25" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="25" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="30" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="30" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="30" width="5" height="5" fill="rgb(74, 56, 38)"/>
<rect x="55" y="30" width="15" height="5" fill="rgb(212, 175, 55)"/>
<rect x="70" y="30" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="30" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="35" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="35" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="35" width="25" height="5" fill="rgb(212, 175, 55)"/>
<rect x="75" y="35" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="40" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="40" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="40" width="5" height="5" fill="rgb(74, 56, 38)"/>
<rect x="55" y="40" width="15" height="5" fill="rgb(212, 175, 55)"/>
<rect x="70" y="40" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="40" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="45" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="45" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="45" width="10" height="5" fill="rgb(74, 56, 38)"/>
<rect x="60" y="45" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="65" y="45" width="5" height="5" fill="rgb(74, 56, 38)"/>
<rect x="70" y="45" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="45" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="50" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="50" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="50" y="50" width="20" height="5" fill="rgb(74, 56, 38)"/>
<rect x="70" y="50" width="5" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="50" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="55" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="45" y="55" width="30" height="5" fill="rgb(94, 74, 50)"/>
<rect x="75" y="55" width="45" height="5" fill="rgb(58, 42, 30)"/>
<rect x="0" y="60" width="35" height="5" fill="rgb(40, 28, 20)"/>
<rect x="35" y="60" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="40" y="60" width="5" height="5" fill="rgb(235, 200, 80)"/>
<rect x="45" y="60" width="75" height="5" fill="rgb(40, 28, 20)"/>
<rect x="0" y="65" width="15" height="5" fill="rgb(40, 28, 20)"/>
<rect x="15" y="65" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="20" y="65" width="5" height="5" fill="rgb(235, 200, 80)"/>
<rect x="25" y="65" width="70" height="5" fill="rgb(40, 28, 20)"/>
<rect x="95" y="65" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="100" y="65" width="5" height="5" fill="rgb(235, 200, 80)"/>
<rect x="105" y="65" width="15" height="5" fill="rgb(40, 28, 20)"/>
<rect x="0" y="70" width="25" height="5" fill="rgb(40, 28, 20)"/>
<rect x="25" y="70" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="30" y="70" width="5" height="5" fill="rgb(235, 200, 80)"/>
<rect x="35" y="70" width="50" height="5" fill="rgb(40, 28, 20)"/>
<rect x="85" y="70" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="90" y="70" width="5" height="5" fill="rgb(235, 200, 80)"/>
<rect x="95" y="70" width="5" height="5" fill="rgb(40, 28, 20)"/>
<rect x="100" y="70" width="5" height="5" fill="rgb(212, 175, 55)"/>
<rect x="105" y="70" width="5" height="5" fill="rgb(235, 200, 80)"/>
<rect x="110" y="70" width="10" height="5" fill="rgb(40, 28, 20)"/>
<rect x="0" y="75" width="120" height="5" fill="rgb(40, 28, 20)"/>
</svg>`);
}

function habitatRoughTerrain() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="10" width="120" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="15" width="50" height="5" fill="rgb(120, 70, 100)"/>
<rect x="50" y="15" width="5" height="5" fill="rgb(230, 120, 40)"/>
<rect x="55" y="15" width="65" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="20" width="50" height="5" fill="rgb(120, 70, 100)"/>
<rect x="50" y="20" width="5" height="5" fill="rgb(230, 120, 40)"/>
<rect x="55" y="20" width="40" height="5" fill="rgb(120, 70, 100)"/>
<rect x="95" y="20" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="100" y="20" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="25" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="20" y="25" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="25" y="25" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="45" y="25" width="15" height="5" fill="rgb(230, 120, 40)"/>
<rect x="60" y="25" width="5" height="5" fill="rgb(120, 70, 100)"/>
<rect x="65" y="25" width="5" height="5" fill="rgb(230, 120, 40)"/>
<rect x="70" y="25" width="25" height="5" fill="rgb(120, 70, 100)"/>
<rect x="95" y="25" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="100" y="25" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="30" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="20" y="30" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="25" y="30" width="40" height="5" fill="rgb(120, 70, 100)"/>
<rect x="65" y="30" width="5" height="5" fill="rgb(230, 120, 40)"/>
<rect x="70" y="30" width="25" height="5" fill="rgb(120, 70, 100)"/>
<rect x="95" y="30" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="100" y="30" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="35" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="20" y="35" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="25" y="35" width="35" height="5" fill="rgb(120, 70, 100)"/>
<rect x="60" y="35" width="15" height="5" fill="rgb(230, 120, 40)"/>
<rect x="75" y="35" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="95" y="35" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="100" y="35" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="40" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="20" y="40" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="25" y="40" width="70" height="5" fill="rgb(120, 70, 100)"/>
<rect x="95" y="40" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="100" y="40" width="20" height="5" fill="rgb(120, 70, 100)"/>
<rect x="0" y="45" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="5" y="45" width="10" height="5" fill="rgb(150, 90, 60)"/>
<rect x="15" y="45" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="20" y="45" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="25" y="45" width="5" height="5" fill="rgb(60, 34, 26)"/>
<rect x="30" y="45" width="15" height="5" fill="rgb(150, 90, 60)"/>
<rect x="45" y="45" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="50" y="45" width="40" height="5" fill="rgb(150, 90, 60)"/>
<rect x="90" y="45" width="10" height="5" fill="rgb(60, 34, 26)"/>
<rect x="100" y="45" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="105" y="45" width="15" height="5" fill="rgb(150, 90, 60)"/>
<rect x="0" y="50" width="20" height="5" fill="rgb(150, 90, 60)"/>
<rect x="20" y="50" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="25" y="50" width="10" height="5" fill="rgb(150, 90, 60)"/>
<rect x="35" y="50" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="40" y="50" width="75" height="5" fill="rgb(150, 90, 60)"/>
<rect x="115" y="50" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="0" y="55" width="15" height="5" fill="rgb(150, 90, 60)"/>
<rect x="15" y="55" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="20" y="55" width="100" height="5" fill="rgb(150, 90, 60)"/>
<rect x="0" y="60" width="10" height="5" fill="rgb(110, 62, 44)"/>
<rect x="10" y="60" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="15" y="60" width="5" height="5" fill="rgb(110, 62, 44)"/>
<rect x="20" y="60" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="25" y="60" width="15" height="5" fill="rgb(110, 62, 44)"/>
<rect x="40" y="60" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="45" y="60" width="40" height="5" fill="rgb(110, 62, 44)"/>
<rect x="85" y="60" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="90" y="60" width="30" height="5" fill="rgb(110, 62, 44)"/>
<rect x="0" y="65" width="15" height="5" fill="rgb(110, 62, 44)"/>
<rect x="15" y="65" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="20" y="65" width="20" height="5" fill="rgb(110, 62, 44)"/>
<rect x="40" y="65" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="45" y="65" width="50" height="5" fill="rgb(110, 62, 44)"/>
<rect x="95" y="65" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="100" y="65" width="20" height="5" fill="rgb(110, 62, 44)"/>
<rect x="0" y="70" width="65" height="5" fill="rgb(110, 62, 44)"/>
<rect x="65" y="70" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="70" y="70" width="15" height="5" fill="rgb(110, 62, 44)"/>
<rect x="85" y="70" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="90" y="70" width="30" height="5" fill="rgb(110, 62, 44)"/>
<rect x="0" y="75" width="10" height="5" fill="rgb(110, 62, 44)"/>
<rect x="10" y="75" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="15" y="75" width="25" height="5" fill="rgb(110, 62, 44)"/>
<rect x="40" y="75" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="45" y="75" width="20" height="5" fill="rgb(110, 62, 44)"/>
<rect x="65" y="75" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="70" y="75" width="10" height="5" fill="rgb(110, 62, 44)"/>
<rect x="80" y="75" width="5" height="5" fill="rgb(90, 48, 34)"/>
<rect x="85" y="75" width="25" height="5" fill="rgb(110, 62, 44)"/>
<rect x="110" y="75" width="10" height="5" fill="rgb(90, 48, 34)"/>
</svg>`);
}

function habitatSea() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="10" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="10" y="10" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="20" y="10" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="30" y="10" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="40" y="10" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="50" y="10" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="60" y="10" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="70" y="10" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="80" y="10" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="90" y="10" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="100" y="10" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="110" y="10" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="15" width="120" height="5" fill="rgb(40, 110, 190)"/>
<rect x="0" y="20" width="120" height="5" fill="rgb(40, 110, 190)"/>
<rect x="0" y="25" width="120" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="30" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="10" y="30" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="20" y="30" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="30" y="30" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="40" y="30" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="50" y="30" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="60" y="30" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="70" y="30" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="80" y="30" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="90" y="30" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="100" y="30" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="110" y="30" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="35" width="120" height="5" fill="rgb(52, 130, 205)"/>
<rect x="0" y="40" width="120" height="5" fill="rgb(52, 130, 205)"/>
<rect x="0" y="45" width="120" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="50" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="10" y="50" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="20" y="50" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="30" y="50" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="40" y="50" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="50" y="50" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="60" y="50" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="70" y="50" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="80" y="50" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="90" y="50" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="100" y="50" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="110" y="50" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="55" width="120" height="5" fill="rgb(70, 150, 215)"/>
<rect x="0" y="60" width="120" height="5" fill="rgb(70, 150, 215)"/>
<rect x="0" y="65" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="10" y="65" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="20" y="65" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="30" y="65" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="40" y="65" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="50" y="65" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="60" y="65" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="70" y="65" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="80" y="65" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="90" y="65" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="100" y="65" width="10" height="5" fill="rgb(200, 230, 250)"/>
<rect x="110" y="65" width="10" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="70" width="120" height="5" fill="rgb(26, 88, 168)"/>
<rect x="0" y="75" width="120" height="5" fill="rgb(26, 88, 168)"/>
</svg>`);
}

function habitatUrban() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="10" width="120" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="15" width="120" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="20" width="100" height="5" fill="rgb(36, 30, 70)"/>
<rect x="100" y="20" width="5" height="5" fill="rgb(255, 255, 255)"/>
<rect x="105" y="20" width="15" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="25" width="80" height="5" fill="rgb(36, 30, 70)"/>
<rect x="80" y="25" width="15" height="5" fill="rgb(50, 44, 84)"/>
<rect x="95" y="25" width="25" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="30" width="45" height="5" fill="rgb(36, 30, 70)"/>
<rect x="45" y="30" width="15" height="5" fill="rgb(50, 44, 84)"/>
<rect x="60" y="30" width="20" height="5" fill="rgb(36, 30, 70)"/>
<rect x="80" y="30" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="85" y="30" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="90" y="30" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="95" y="30" width="25" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="35" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="5" y="35" width="20" height="5" fill="rgb(50, 44, 84)"/>
<rect x="25" y="35" width="20" height="5" fill="rgb(36, 30, 70)"/>
<rect x="45" y="35" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="50" y="35" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="55" y="35" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="60" y="35" width="20" height="5" fill="rgb(36, 30, 70)"/>
<rect x="80" y="35" width="15" height="5" fill="rgb(50, 44, 84)"/>
<rect x="95" y="35" width="25" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="40" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="5" y="40" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="10" y="40" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="15" y="40" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="20" y="40" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="25" y="40" width="20" height="5" fill="rgb(36, 30, 70)"/>
<rect x="45" y="40" width="40" height="5" fill="rgb(50, 44, 84)"/>
<rect x="85" y="40" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="90" y="40" width="25" height="5" fill="rgb(50, 44, 84)"/>
<rect x="115" y="40" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="45" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="5" y="45" width="45" height="5" fill="rgb(50, 44, 84)"/>
<rect x="50" y="45" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="55" y="45" width="10" height="5" fill="rgb(50, 44, 84)"/>
<rect x="65" y="45" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="70" y="45" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="75" y="45" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="80" y="45" width="20" height="5" fill="rgb(50, 44, 84)"/>
<rect x="100" y="45" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="105" y="45" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="110" y="45" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="115" y="45" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="50" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="5" y="50" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="10" y="50" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="15" y="50" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="20" y="50" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="25" y="50" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="30" y="50" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="35" y="50" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="40" y="50" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="45" y="50" width="40" height="5" fill="rgb(50, 44, 84)"/>
<rect x="85" y="50" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="90" y="50" width="25" height="5" fill="rgb(50, 44, 84)"/>
<rect x="115" y="50" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="55" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="5" y="55" width="45" height="5" fill="rgb(50, 44, 84)"/>
<rect x="50" y="55" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="55" y="55" width="10" height="5" fill="rgb(50, 44, 84)"/>
<rect x="65" y="55" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="70" y="55" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="75" y="55" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="80" y="55" width="20" height="5" fill="rgb(50, 44, 84)"/>
<rect x="100" y="55" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="105" y="55" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="110" y="55" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="115" y="55" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="60" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="5" y="60" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="10" y="60" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="15" y="60" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="20" y="60" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="25" y="60" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="30" y="60" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="35" y="60" width="5" height="5" fill="rgb(50, 44, 84)"/>
<rect x="40" y="60" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="45" y="60" width="40" height="5" fill="rgb(50, 44, 84)"/>
<rect x="85" y="60" width="5" height="5" fill="rgb(255, 224, 120)"/>
<rect x="90" y="60" width="25" height="5" fill="rgb(50, 44, 84)"/>
<rect x="115" y="60" width="5" height="5" fill="rgb(36, 30, 70)"/>
<rect x="0" y="65" width="120" height="5" fill="rgb(24, 20, 46)"/>
<rect x="0" y="70" width="120" height="5" fill="rgb(24, 20, 46)"/>
<rect x="0" y="75" width="120" height="5" fill="rgb(24, 20, 46)"/>
</svg>`);
}

function habitatWatersEdge() {
    return svgDataUri(`<svg viewBox="0 0 120 80" xmlns="http://www.w3.org/2000/svg" shape-rendering="crispEdges">
<rect x="0" y="0" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="5" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="10" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="5" y="10" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="25" y="10" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="30" y="10" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="50" y="10" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="55" y="10" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="75" y="10" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="80" y="10" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="100" y="10" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="105" y="10" width="15" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="15" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="20" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="25" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="5" y="25" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="25" y="25" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="30" y="25" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="50" y="25" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="55" y="25" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="75" y="25" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="80" y="25" width="20" height="5" fill="rgb(58, 150, 210)"/>
<rect x="100" y="25" width="5" height="5" fill="rgb(220, 240, 250)"/>
<rect x="105" y="25" width="15" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="30" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="35" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="40" width="120" height="5" fill="rgb(58, 150, 210)"/>
<rect x="0" y="45" width="90" height="5" fill="rgb(110, 190, 225)"/>
<rect x="90" y="45" width="15" height="5" fill="rgb(60, 150, 70)"/>
<rect x="105" y="45" width="15" height="5" fill="rgb(110, 190, 225)"/>
<rect x="0" y="50" width="20" height="5" fill="rgb(110, 190, 225)"/>
<rect x="20" y="50" width="15" height="5" fill="rgb(60, 150, 70)"/>
<rect x="35" y="50" width="50" height="5" fill="rgb(110, 190, 225)"/>
<rect x="85" y="50" width="25" height="5" fill="rgb(60, 150, 70)"/>
<rect x="110" y="50" width="10" height="5" fill="rgb(110, 190, 225)"/>
<rect x="0" y="55" width="15" height="5" fill="rgb(222, 198, 145)"/>
<rect x="15" y="55" width="25" height="5" fill="rgb(60, 150, 70)"/>
<rect x="40" y="55" width="40" height="5" fill="rgb(222, 198, 145)"/>
<rect x="80" y="55" width="35" height="5" fill="rgb(60, 150, 70)"/>
<rect x="115" y="55" width="5" height="5" fill="rgb(222, 198, 145)"/>
<rect x="0" y="60" width="10" height="5" fill="rgb(222, 198, 145)"/>
<rect x="10" y="60" width="35" height="5" fill="rgb(60, 150, 70)"/>
<rect x="45" y="60" width="45" height="5" fill="rgb(222, 198, 145)"/>
<rect x="90" y="60" width="10" height="5" fill="rgb(150, 100, 60)"/>
<rect x="100" y="60" width="20" height="5" fill="rgb(222, 198, 145)"/>
<rect x="0" y="65" width="20" height="5" fill="rgb(222, 198, 145)"/>
<rect x="20" y="65" width="10" height="5" fill="rgb(150, 100, 60)"/>
<rect x="30" y="65" width="60" height="5" fill="rgb(222, 198, 145)"/>
<rect x="90" y="65" width="10" height="5" fill="rgb(150, 100, 60)"/>
<rect x="100" y="65" width="20" height="5" fill="rgb(222, 198, 145)"/>
<rect x="0" y="70" width="20" height="5" fill="rgb(222, 198, 145)"/>
<rect x="20" y="70" width="10" height="5" fill="rgb(150, 100, 60)"/>
<rect x="30" y="70" width="60" height="5" fill="rgb(222, 198, 145)"/>
<rect x="90" y="70" width="10" height="5" fill="rgb(150, 100, 60)"/>
<rect x="100" y="70" width="20" height="5" fill="rgb(222, 198, 145)"/>
<rect x="0" y="75" width="20" height="5" fill="rgb(222, 198, 145)"/>
<rect x="20" y="75" width="10" height="5" fill="rgb(150, 100, 60)"/>
<rect x="30" y="75" width="90" height="5" fill="rgb(222, 198, 145)"/>
</svg>`);
}

// Habitat name (as the server sends it) -> the finished background image.
// Called once here, at startup, so the SVG text is only built one time
// rather than on every pokemon.
const HABITAT_BACKGROUNDS = {
    "Cave": habitatCave(),
    "Forest": habitatForest(),
    "Grassland": habitatGrassland(),
    "Mountain": habitatMountain(),
    "Rare": habitatRare(),
    "Rough Terrain": habitatRoughTerrain(),
    "Sea": habitatSea(),
    "Urban": habitatUrban(),
    "Waters Edge": habitatWatersEdge(),
};
const DEFAULT_HABITAT_BG = habitatGrassland();  // for pokemon with no habitat listed

// ---------------------------------------------------------------
// HAND-DRAWN PIXEL ICONS
// Little inline SVGs for the info pills: a ruler for height, a kettlebell
// for weight, and so on. Each one is a handful of rectangles.
//
// fill="currentColor" is the trick that makes these reusable -- it means
// "whatever text colour this sits inside", so one icon works on a dark
// pill and a light one without needing two copies.
// ---------------------------------------------------------------
const RULER_ICON = `
<svg viewBox="0 0 16 8" xmlns="http://www.w3.org/2000/svg">
    <rect x="0" y="2" width="16" height="4" fill="currentColor"/>
    <rect x="2" y="2" width="1" height="2" fill="black" opacity="0.35"/>
    <rect x="5" y="2" width="1" height="2" fill="black" opacity="0.35"/>
    <rect x="8" y="2" width="1" height="2" fill="black" opacity="0.35"/>
    <rect x="11" y="2" width="1" height="2" fill="black" opacity="0.35"/>
    <rect x="14" y="2" width="1" height="2" fill="black" opacity="0.35"/>
</svg>`;

const KETTLEBELL_ICON = `
<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
    <rect x="4" y="0" width="4" height="2" fill="currentColor"/>
    <rect x="3" y="2" width="6" height="1" fill="currentColor"/>
    <rect x="2" y="3" width="8" height="7" fill="currentColor"/>
    <rect x="3" y="10" width="6" height="1" fill="currentColor"/>
</svg>`;

const EGG_ICON = `
<svg viewBox="0 0 10 12" xmlns="http://www.w3.org/2000/svg">
    <rect x="3" y="0" width="4" height="1" fill="currentColor"/>
    <rect x="2" y="1" width="6" height="2" fill="currentColor"/>
    <rect x="1" y="3" width="8" height="3" fill="currentColor"/>
    <rect x="0" y="6" width="10" height="4" fill="currentColor"/>
    <rect x="1" y="10" width="8" height="1" fill="currentColor"/>
    <rect x="3" y="11" width="4" height="1" fill="currentColor"/>
</svg>`;

const HABITAT_ICON = `
<svg viewBox="0 0 12 10" xmlns="http://www.w3.org/2000/svg">
    <rect x="1" y="7" width="10" height="2" fill="currentColor" opacity="0.5"/>
    <rect x="1" y="4" width="2" height="3" fill="currentColor"/>
    <rect x="3" y="2" width="2" height="5" fill="currentColor"/>
    <rect x="5" y="5" width="2" height="2" fill="currentColor"/>
    <rect x="7" y="1" width="2" height="6" fill="currentColor"/>
    <rect x="9" y="3" width="2" height="4" fill="currentColor"/>
</svg>`;

const COLOR_ICON = `
<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <radialGradient id="colorGrad" cx="40%" cy="40%">
            <stop offset="0%" style="stop-color:#ff6b6b;stop-opacity:1"/>
            <stop offset="25%" style="stop-color:#ffd93d;stop-opacity:1"/>
            <stop offset="50%" style="stop-color:#6bcf7f;stop-opacity:1"/>
            <stop offset="75%" style="stop-color:#4a90e2;stop-opacity:1"/>
            <stop offset="100%" style="stop-color:#d946ef;stop-opacity:1"/>
        </radialGradient>
    </defs>
    <circle cx="6" cy="6" r="5" fill="url(#colorGrad)" stroke="#333" stroke-width="0.3"/>
</svg>`;

// The TM/HM icon: a little record/disc. It's a function rather than a
// constant because the label in the middle gets coloured by the move's
// type, so each one is built fresh.
function vinylIcon(labelColor) {
    return `
    <svg class="vinyl-icon" viewBox="0 0 14 14" xmlns="http://www.w3.org/2000/svg">
        <rect x="5" y="1" width="4" height="1" fill="#222"/>
        <rect x="3" y="2" width="8" height="1" fill="#222"/>
        <rect x="2" y="3" width="10" height="1" fill="#222"/>
        <rect x="1" y="4" width="12" height="6" fill="#222"/>
        <rect x="2" y="10" width="10" height="1" fill="#222"/>
        <rect x="3" y="11" width="8" height="1" fill="#222"/>
        <rect x="5" y="12" width="4" height="1" fill="#222"/>
        <rect x="5" y="5" width="4" height="4" fill="${labelColor}"/>
        <rect x="6" y="6" width="2" height="2" fill="#111"/>
    </svg>`;
}

// ---------------------------------------------------------------
// EGG GROUP ICONS (15 total)
// One small drawing per breeding group: a ladybug for Bug, a dinosaur
// skull for Dragon, a butterfly for Fairy, and so on. Unlike the habitat
// scenes these were drawn by hand here, using proper SVG shapes
// (circles, polygons) rather than a grid of squares.
// ---------------------------------------------------------------
const EGG_GROUP_ICONS = {
    bug: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="5" r="3" fill="#e74c3c"/>
        <rect x="5" y="2" width="2" height="2" fill="#000"/>
        <rect x="5" y="5" width="2" height="2" fill="#000"/>
        <polygon points="4,6 3,8 5,7" fill="#ff6b35"/>
        <polygon points="8,6 9,8 7,7" fill="#ff6b35"/>
    </svg>`,
    ditto: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="6" cy="6" rx="4" ry="4.5" fill="#c977d1"/>
        <circle cx="5" cy="4.5" r="1" fill="#000"/>
        <circle cx="7" cy="4.5" r="1" fill="#000"/>
        <path d="M 6 7 Q 5.5 8 6 8.5 Q 6.5 8 6 7" fill="#9d5ba8"/>
    </svg>`,
    dragon: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <polygon points="6,2 8,5 7,8 6,9 5,8 4,5" fill="#d1a54a"/>
        <circle cx="5.5" cy="5" r="0.8" fill="#2d2d2d"/>
        <circle cx="6.5" cy="5" r="0.8" fill="#2d2d2d"/>
        <polygon points="5,7 6,9 7,7" fill="#3d3d3d"/>
    </svg>`,
    fairy: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="6" cy="4" rx="3" ry="2.5" fill="#ff69b4"/>
        <polygon points="4,5 3,8 4,7" fill="#c977d1"/>
        <polygon points="8,5 9,8 8,7" fill="#c977d1"/>
        <polygon points="5,3 4,2 5,2" fill="#fff"/>
        <polygon points="7,3 8,2 7,2" fill="#fff"/>
    </svg>`,
    flying: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <polygon points="3,6 6,2 9,6 7,8 6,9 5,8" fill="#7a5fd1"/>
        <polygon points="4,7 5,8 4,8" fill="#5a4fb1"/>
        <polygon points="8,7 7,8 8,8" fill="#5a4fb1"/>
    </svg>`,
    humanshape: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <circle cx="6" cy="2.5" r="1.2" fill="#8B6F47"/>
        <rect x="5" y="4" width="2" height="3" fill="#A0826D"/>
        <rect x="4" y="4" width="1.5" height="4" fill="#8B6F47"/>
        <rect x="6.5" y="4" width="1.5" height="4" fill="#8B6F47"/>
    </svg>`,
    indeterminate: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <text x="6" y="8" font-size="8" font-weight="bold" fill="#e74c3c" text-anchor="middle">!</text>
        <text x="6" y="10.5" font-size="7" font-weight="bold" fill="#e74c3c" text-anchor="middle">!</text>
    </svg>`,
    mineral: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <polygon points="6,1 10,4 9,9 3,9 2,4" fill="#5dade2"/>
        <polygon points="6,1 8,3 9,2" fill="#fff"/>
        <polygon points="9,4 10,4 9,7" fill="#aed6f1"/>
    </svg>`,
    monster: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <polygon points="3,5 4,2 6,1 8,2 9,5 8,9 4,9" fill="#52be80"/>
        <circle cx="4.5" cy="3" r="0.8" fill="#000"/>
        <circle cx="7.5" cy="3" r="0.8" fill="#000"/>
        <polygon points="5,7 6,8 7,7" fill="#1e8449"/>
    </svg>`,
    "no-eggs": `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <path d="M 6 1 Q 4 3 4 5 Q 4 8 6 9 Q 8 8 8 5 Q 8 3 6 1" fill="#f5f5f5" stroke="#ccc" stroke-width="0.5"/>
        <circle cx="5" cy="4" r="0.4" fill="#52be80"/>
        <circle cx="6.5" cy="5" r="0.4" fill="#52be80"/>
        <line x1="3.5" y1="6.5" x2="8.5" y2="3.5" stroke="#e74c3c" stroke-width="0.5"/>
        <line x1="8.5" y1="6.5" x2="3.5" y2="3.5" stroke="#e74c3c" stroke-width="0.5"/>
    </svg>`,
    plant: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="6" cy="7" rx="2.5" ry="2" fill="#4c9a2a"/>
        <ellipse cx="4" cy="4" rx="1.8" ry="2.5" fill="#52be80"/>
        <ellipse cx="8" cy="4" rx="1.8" ry="2.5" fill="#52be80"/>
        <ellipse cx="6" cy="2" rx="1.5" ry="2" fill="#6abf59"/>
    </svg>`,
    water1: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <path d="M 6 1 Q 4.5 2 4.5 4 Q 4.5 6 6 7.5 Q 7.5 6 7.5 4 Q 7.5 2 6 1" fill="#3aa0d6"/>
        <text x="6" y="5.5" font-size="2.5" font-weight="bold" fill="#fff" text-anchor="middle">1</text>
    </svg>`,
    water2: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <path d="M 6 1 Q 4.5 2 4.5 4 Q 4.5 6 6 7.5 Q 7.5 6 7.5 4 Q 7.5 2 6 1" fill="#3aa0d6"/>
        <text x="6" y="5.5" font-size="2.5" font-weight="bold" fill="#fff" text-anchor="middle">2</text>
    </svg>`,
    water3: `<svg viewBox="0 0 12 12" xmlns="http://www.w3.org/2000/svg">
        <path d="M 6 1 Q 4.5 2 4.5 4 Q 4.5 6 6 7.5 Q 7.5 6 7.5 4 Q 7.5 2 6 1" fill="#3aa0d6"/>
        <text x="6" y="5.5" font-size="2.5" font-weight="bold" fill="#fff" text-anchor="middle">3</text>
    </svg>`,
};

function getEggGroupIcon(groupName) {
    // The server sends "Water 1", the key here is "water1" -- so lowercase
    // it and strip the spaces before looking it up. Falls back to a plain
    // egg if it's a group we haven't drawn.
    const normalized = groupName.toLowerCase().replace(/\s+/g, "");
    return EGG_GROUP_ICONS[normalized] || EGG_ICON;
}

// ---------------------------------------------------------------
// GRAB ALL THE HTML ELEMENTS WE'LL NEED TO UPDATE
//
// Done once, here, rather than looking each one up every time it's needed
// -- searching the page repeatedly is wasteful and makes the render code
// noisier. Anything that only exists in one of the two themes will be
// null here, which is why later code keeps saying `if (thing)`.
// ---------------------------------------------------------------
const appEl = document.getElementById("app");

const searchInput = document.getElementById("search-input");
const searchSuggestionsEl = document.getElementById("search-suggestions");
const flipPrevBtn = document.getElementById("flip-prev");
const flipNextBtn = document.getElementById("flip-next");
const shellNavPrevBtn = document.getElementById("shell-nav-prev");
const shellNavNextBtn = document.getElementById("shell-nav-next");

const pokemonNameEl = document.getElementById("pokemon-name");
const dexNumberEl = document.getElementById("dex-number");
const backToBaseBtn = document.getElementById("back-to-base-btn");
const spriteImageEl = document.getElementById("sprite-image");
const spriteVariantTagEl = document.getElementById("sprite-variant-tag");

const typeBadgesRowEl = document.getElementById("type-badges-row");
const infoPoupupWindowEl = document.getElementById("info-popup-window");
const typeRowPillsEl = document.getElementById("type-row-pills");
const typeRowMatchupsEl = document.getElementById("type-row-matchups");

const bioPillsRowEl = document.getElementById("bio-pills-row");
const fieldSurveyBodyEl = document.getElementById("field-survey-body");

const descriptionVersionEl = document.getElementById("description-version");
const descriptionTextEl = document.getElementById("description-text");
const descPrevBtn = document.getElementById("desc-prev");
const descNextBtn = document.getElementById("desc-next");

const mapGenPrevBtn = document.getElementById("map-gen-prev");
const mapGenNextBtn = document.getElementById("map-gen-next");
const mapGenTitleEl = document.getElementById("map-gen-title");
const mapImageWrapEl = document.getElementById("map-image-wrap");
const mapImageEl = document.getElementById("map-image");
const mapPinsEl = document.getElementById("map-pins");
const mapLocationListEl = document.getElementById("map-location-list");

const typeModalOverlay = document.getElementById("type-modal-overlay");
const typeModalClose = document.getElementById("type-modal-close");
const typeChartGridEl = document.getElementById("type-chart-grid");

const assetPopoverOverlay = document.getElementById("asset-popover-overlay");
const assetPopoverClose = document.getElementById("asset-popover-close");
const assetPopoverTitleEl = document.getElementById("asset-popover-title");
const assetPopoverBodyEl = document.getElementById("asset-popover-body");

const spritePrevBtn = document.getElementById("sprite-prev");
const spriteNextBtn = document.getElementById("sprite-next");

const shellNameInput = document.getElementById("shell-name-input");
const shellSearchSuggestionsEl = document.getElementById("shell-search-suggestions");
const shellDexBadgeEl = document.getElementById("shell-dex-badge");

const carouselPrevBtn = document.getElementById("carousel-prev");
const carouselNextBtn = document.getElementById("carousel-next");
const carouselTitleEl = document.getElementById("carousel-title");

const statsListEl = document.getElementById("stats-list");
const abilitiesListEl = document.getElementById("abilities-list");
const movesListEl = document.getElementById("moves-list");
const tmhmListEl = document.getElementById("tmhm-list");
const formsListEl = document.getElementById("forms-list");
const evolutionListEl = document.getElementById("evolution-list");

// ---------------------------------------------------------------
// STATE
//
// Everything the app currently "knows". There's no framework here, so
// this handful of variables IS the app's memory: change one, then call
// the matching render function to make the page catch up.
// ---------------------------------------------------------------
let currentPokemon = null;      // the full blob the server sent us
let currentVariant = null;      // a Mega/Gmax/regional form, if one is open
let currentSpriteIndex = 0;     // which of the 4 sprite pictures is showing
let currentSlideIndex = 0;      // which carousel slide (stats/moves/...)
let currentDescIndex = 0;       // which game's pokedex entry is showing
let minDexNo = 1;               // filled in by loadMeta()
let maxDexNo = 1025;            // ditto -- these bound the prev/next arrows
let statRanges = {};            // real min/max per stat, for the bar colours
let searchDebounceTimer = null; // see the search listener at the bottom
let typeChartCache = null;      // the type chart never changes; fetch once
let mapGenerations = [];        // encounter locations, grouped into map tabs
let currentMapGenIndex = 0;     // which map tab is showing

// Field Survey only exists in the Pokedex shell markup -- the Clean view
// shows that same bio data as pills under the sprite instead. Filter to
// whichever slides are actually present so both themes share one carousel.
const slides = [
    { id: "slide-battle", title: "Battle Info" },
    { id: "slide-moves", title: "Moves" },
    { id: "slide-tmhm", title: "TM / HM" },
    { id: "slide-forms", title: "Forms" },
    { id: "slide-evolution", title: "Evolution" },
    { id: "slide-field-survey", title: "Field Survey" },
].filter(s => document.getElementById(s.id) !== null);

const STAT_LABELS = { hp: "HP", attack: "ATK", defense: "DEF", sp_atk: "SPA", sp_def: "SPD", speed: "SPE" };

// ---------------------------------------------------------------
// METADATA (dex bounds + real stat min/max for the bar gradients)
// ---------------------------------------------------------------
// "async" + "await" = "go and fetch this, and don't freeze the page while
// you wait". Every function that talks to the server is written this way.
async function loadMeta() {
    const response = await fetch("/api/meta");
    const data = await response.json();
    minDexNo = data.min_dex_no;
    maxDexNo = data.max_dex_no;
    statRanges = data.stat_ranges;
}

// ---------------------------------------------------------------
// FETCH A POKEMON AND RENDER EVERYTHING
//
// This is the heart of the app. Everything that changes what's on screen
// -- searching, the prev/next arrows, clicking an evolution -- ends up
// calling this one function. Ask the server for the pokemon, save it,
// reset the various carousels to the start, then redraw each part of the
// page in turn.
// ---------------------------------------------------------------
async function loadPokemon(dexNo) {
    const response = await fetch(`/api/pokemon/${dexNo}`);
    const data = await response.json();

    if (data.error) {
        descriptionTextEl.textContent = data.error;
        return;
    }

    currentPokemon = data;
    currentVariant = null;
    currentSpriteIndex = 0;
    currentSlideIndex = 0;
    currentDescIndex = 0;
    // cleared before renderDescription() so its map sync can't act on the
    // previous pokemon's regions; loadMapData() repopulates it below
    mapGenerations = [];
    currentMapGenIndex = 0;
    closeAssetPopover();

    // Redraw every part of the page. Each render function reads from the
    // state above and rewrites one chunk of HTML.
    renderHabitat();
    renderIdentity();   // name, dex#, sprite, type row + matchups, battle slide
    renderDescription();
    renderBioPills();
    renderMovesSlide();
    renderTmHmSlide();
    renderFormsSlide();
    renderEvolutionSlide();
    renderCarouselPosition();
    loadMapData();
}

// ---------------------------------------------------------------
// IDENTITY (swaps between base pokemon and a Mega/Gmax/regional variant)
// ---------------------------------------------------------------

function renderIdentity() {
    // Name, dex number, sprite, types, stats. Called both on load and
    // whenever you click into (or back out of) an alternate form.
    //
    // `source` is the "who are we actually showing" pointer: the variant
    // if one is open, otherwise the base pokemon. Several functions below
    // do the same thing, so a Mega's stats show instead of the base one's.
    const showingVariant = currentVariant !== null;
    const source = showingVariant ? currentVariant : currentPokemon;

    pokemonNameEl.textContent = source.display_name;
    // padStart(3, "0") turns 6 into "006", the way a real dex shows it.
    dexNumberEl.textContent = "#" + String(currentPokemon.national_dex_no).padStart(3, "0");
    backToBaseBtn.classList.toggle("hidden", !showingVariant);

    if (shellNameInput) shellNameInput.value = source.display_name;
    if (shellDexBadgeEl) shellDexBadgeEl.textContent = "#" + String(currentPokemon.national_dex_no).padStart(3, "0");

    renderTheme(source.stats.type1);
    renderSprite();
    renderTypeRow(source.stats);
    renderBattleSlide(source);
}

function renderTheme(primaryType) {
    // Set on <html>, not #app -- the type-chart modal and the asset
    // popover are siblings of #app (not descendants), so a variable set
    // on #app never reaches them. :root is visible to the whole document.
    const color = TYPE_COLORS[primaryType] || DEFAULT_COLOR;
    document.documentElement.style.setProperty("--type-color", color);
}

function renderHabitat() {
    const habitat = currentPokemon.biological.habitat;
    document.documentElement.style.setProperty("--habitat-bg", HABITAT_BACKGROUNDS[habitat] || DEFAULT_HABITAT_BG);
}

function renderSprite() {
    // Show whichever of the (up to 4) sprite pictures is currently
    // selected. The % below wraps the index around, so clicking "next"
    // past the last sprite loops back to the first.
    const source = currentVariant !== null ? currentVariant : currentPokemon;
    const sprites = source.sprites_available;

    if (sprites.length === 0) {
        spriteImageEl.src = "";
        spriteVariantTagEl.textContent = "";
        return;
    }

    currentSpriteIndex = currentSpriteIndex % sprites.length;
    const sprite = sprites[currentSpriteIndex];
    spriteImageEl.src = sprite.url;
    renderSpriteVariantTag(source.display_name, sprite.type);
}

// The little label under the sprite, e.g. "Pikachu: Shiny".
function renderSpriteVariantTag(displayName, spriteType) {
    const SUFFIXES = {
        "front_default": "",
        "front_shiny": ": Shiny",
        "front_female": ": Female",
        "front_shiny_female": ": Shiny Female",
    };
    spriteVariantTagEl.textContent = displayName + (SUFFIXES[spriteType] || "");
    spriteVariantTagEl.classList.toggle("shiny-tag", spriteType.includes("shiny"));
}

// ---------------------------------------------------------------
// TYPE ROW: pills on the left, compact matchup chips on the right
// ---------------------------------------------------------------

function renderTypeRow(stats) {
    // In Pokedex view, render type badges to the center screen
    if (document.body.classList.contains("pokedex-theme")) {
        renderTypeBadges(stats.type1, stats.type2);
    } else {
        // In clean view, render to the type-row-pills
        typeRowPillsEl.innerHTML = buildTypePillsHtml(stats.type1, stats.type2);
        attachTypePillHandlers(typeRowPillsEl);
        // Notable-matchups chips + the full type chart modal aren't in the
        // Pokedex shell's markup right now -- pulled out until there's a
        // place for them there (still present on the clean view).
        if (typeRowMatchupsEl) renderTypeMatchupChips(stats.type1, stats.type2);
    }
}

function renderTypeBadges(type1, type2) {
    typeBadgesRowEl.innerHTML = buildTypePillsHtml(type1, type2);
    attachTypePillHandlers(typeBadgesRowEl);
}

function buildTypePillsHtml(type1, type2) {
    let html = typePillHtml(type1);
    if (type2) html += typePillHtml(type2);
    return html;
}

function typePillHtml(typeName) {
    const color = TYPE_COLORS[typeName] || DEFAULT_COLOR;
    return `<span class="type-pill" data-type="${typeName}" style="background:${color}">${typeName}</span>`;
}

function attachTypePillHandlers(container) {
    if (!typeModalOverlay) return; // no modal in this theme right now
    container.querySelectorAll(".type-pill").forEach(el => {
        el.addEventListener("click", () => openTypeChartModal(el.getAttribute("data-type")));
    });
}

// Fetch the 18x18 type chart, but only the first time -- after that we
// hand back the copy we already have. It's identical for every pokemon,
// so re-fetching it on every click would be pure waste.
async function getTypeChart() {
    if (typeChartCache === null) {
        const response = await fetch("/api/type-chart");
        typeChartCache = await response.json();
    }
    return typeChartCache;
}

// Works out what this pokemon is weak/resistant to, and shows only the
// interesting ones as little chips.
async function renderTypeMatchupChips(type1, type2) {
    const t1 = type1.toLowerCase();
    const t2 = type2 ? type2.toLowerCase() : null;

    const chart = await getTypeChart();
    // For each of the 18 attacking types, how much damage would it do?
    // For a dual-type pokemon you MULTIPLY the two: something that's 2x
    // against both of its types hits for 4x. (?? 1 means "if that lookup
    // came back empty, treat it as normal damage".)
    const rows = chart.types.map(attackingType => {
        const m1 = chart.matchup[attackingType][t1] ?? 1;
        const m2 = t2 ? (chart.matchup[attackingType][t2] ?? 1) : 1;
        return { attackingType, multiplier: m1 * m2 };
    }).filter(r => r.multiplier !== 1);  // drop the boring 1x ones

    rows.sort((a, b) => b.multiplier - a.multiplier);  // biggest threat first

    if (rows.length === 0) {
        typeRowMatchupsEl.innerHTML = `<span style="font-size:11px;color:#aaa;">No notable matchups</span>`;
        return;
    }

    typeRowMatchupsEl.innerHTML = rows.map(r => {
        const displayType = capitalize(r.attackingType);
        const color = TYPE_COLORS[displayType] || DEFAULT_COLOR;
        return `
            <span class="matchup-chip" style="background:${color}" data-type="${displayType}">
                ${r.attackingType.slice(0, 3).toUpperCase()}
                <span class="mult-badge">${formatMultiplier(r.multiplier)}</span>
            </span>
        `;
    }).join("");

    typeRowMatchupsEl.querySelectorAll(".matchup-chip").forEach(el => {
        el.addEventListener("click", () => openTypeChartModal(el.getAttribute("data-type")));
    });
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function formatMultiplier(m) {
    if (m === 0) return "0x";
    if (m === 0.25) return "1/4x";
    if (m === 0.5) return "1/2x";
    return m + "x";
}

function multiplierClass(m) {
    if (m === 0) return "mult-immune";
    if (m > 1) return "mult-weak";
    return "mult-resist";
}

// ---------------------------------------------------------------
// VARIANT SWITCHING (Mega / Gmax / regional forms)
// ---------------------------------------------------------------

async function loadVariant(variantId) {
    const response = await fetch(`/api/pokemon-variant/${variantId}`);
    const data = await response.json();
    if (data.error) return;

    currentVariant = data;
    currentSpriteIndex = 0;
    renderIdentity();
}

function clearVariant() {
    currentVariant = null;
    currentSpriteIndex = 0;
    renderIdentity();
}

// ---------------------------------------------------------------
// BATTLE SLIDE: stat bars (no numeric label, red/yellow/green gradient
// against the real min/max for that stat) + abilities
// ---------------------------------------------------------------

function renderBattleSlide(source) {
    const stats = source.stats;

    statsListEl.innerHTML = Object.keys(STAT_LABELS).map(key => {
        const value = stats[key];
        // How good is this stat, compared to every other pokemon in the
        // game? statRanges came from /api/meta at startup. pct comes out
        // between 0 (worst in the game) and 1 (best), which sets both the
        // bar's width and its colour.
        const range = statRanges[key] || { min: 0, max: value || 1 };
        const pct = range.max > range.min ? (value - range.min) / (range.max - range.min) : 0.5;
        const color = statBarColor(pct);
        return `
            <div class="stat-bar-row">
                <span class="stat-bar-name">${STAT_LABELS[key]}</span>
                <span class="stat-bar-value">${value}</span>
                <div class="stat-bar-track">
                    <div class="stat-bar-fill" style="width:${(pct * 100).toFixed(0)}%; background-color:${color}"></div>
                </div>
            </div>
        `;
    }).join("");

    abilitiesListEl.innerHTML = source.abilities
        .map(a => `<span class="tag clickable" data-ability="${a.ability_name}">${a.ability_name}${a.is_hidden ? " (Hidden)" : ""}</span>`)
        .join("");
    attachAbilityHandlers(abilitiesListEl);
}

// crimson (low) -> yellow (median) -> nuclear green (high)
function statBarColor(pct) {
    // Blend between two colours depending on where pct falls. Below the
    // halfway point we're mixing red->yellow; above it, yellow->green.
    // `t` is how far along that half we are (0 to 1), and then each of
    // r/g/b is just "start + (end - start) * t".
    const RED = [220, 20, 60], YELLOW = [241, 196, 15], GREEN = [57, 255, 20];
    const [c1, c2, t] = pct <= 0.5 ? [RED, YELLOW, pct / 0.5] : [YELLOW, GREEN, (pct - 0.5) / 0.5];
    const r = Math.round(c1[0] + (c2[0] - c1[0]) * t);
    const g = Math.round(c1[1] + (c2[1] - c1[1]) * t);
    const b = Math.round(c1[2] + (c2[2] - c1[2]) * t);
    return `rgb(${r}, ${g}, ${b})`;
}

function attachAbilityHandlers(container) {
    container.querySelectorAll("[data-ability]").forEach(el => {
        el.addEventListener("click", () => showAbilityDetail(el.getAttribute("data-ability")));
    });
}

// ---------------------------------------------------------------
// ASSET POPOVER (move/ability flavor text) -- floating + dismissible,
// never permanently occupies layout space.
// ---------------------------------------------------------------

function showAssetPopover(title, bodyHtml) {
    if (document.body.classList.contains("pokedex-theme")) {
        infoPoupupWindowEl.innerHTML = `<h4 class="info-popup-title">${title}</h4>${bodyHtml}`;
        return;
    }
    assetPopoverTitleEl.textContent = title;
    assetPopoverBodyEl.innerHTML = bodyHtml;
    assetPopoverOverlay.classList.remove("hidden");
}

function closeAssetPopover() {
    if (document.body.classList.contains("pokedex-theme")) {
        infoPoupupWindowEl.innerHTML = `<p class="hint-text">Tap a move or ability to see details here.</p>`;
        return;
    }
    assetPopoverOverlay.classList.add("hidden");
}

async function showMoveDetail(moveName) {
    showAssetPopover(moveName, "<p>Loading...</p>");

    const response = await fetch(`/api/move-detail/${encodeURIComponent(moveName)}`);
    const move = await response.json();

    if (move.error) {
        showAssetPopover("Move", "<p>No data found for this move.</p>");
        return;
    }

    const bodyHtml = `
        <div class="detail-stats">
            ${typePillHtml(move.type)}
            <span class="detail-stat">${move.damage_class || "--"}</span>
            <span class="detail-stat">PWR ${move.power ?? "--"}</span>
            <span class="detail-stat">ACC ${move.accuracy ?? "--"}</span>
            <span class="detail-stat">PP ${move.pp ?? "--"}</span>
        </div>
        <p>${move.flavor_text || move.short_effect || "No description available."}</p>
    `;
    showAssetPopover(move.display_name, bodyHtml);
    const activeBodyEl = document.body.classList.contains("pokedex-theme") ? infoPoupupWindowEl : assetPopoverBodyEl;
    attachTypePillHandlers(activeBodyEl);
}

async function showAbilityDetail(abilityName) {
    showAssetPopover(abilityName, "<p>Loading...</p>");

    const response = await fetch(`/api/ability-detail/${encodeURIComponent(abilityName)}`);
    const ability = await response.json();

    if (ability.error) {
        showAssetPopover("Ability", "<p>No data found for this ability.</p>");
        return;
    }

    showAssetPopover(ability.display_name, `<p>${ability.short_effect || "No effect description available."}</p>`);
}

// ---------------------------------------------------------------
// FULL TYPE CHART MODAL
// ---------------------------------------------------------------

// Builds the full 18x18 grid: attacking types down the left, defending
// types across the top, one cell per pairing.
async function openTypeChartModal(highlightType) {
    const chart = await getTypeChart();
    const types = chart.types;

    // The grid is one long flat list of cells; this CSS line is what tells
    // the browser to wrap it into rows of the right width.
    typeChartGridEl.style.gridTemplateColumns = `56px repeat(${types.length}, 22px)`;

    let html = "";
    html += `<div class="chart-header-cell" style="background:#333"></div>`;  // empty top-left corner
    // Top row: the defending type headers.
    types.forEach(t => {
        const color = TYPE_COLORS[capitalize(t)] || DEFAULT_COLOR;
        html += `<div class="chart-header-cell" style="background:${color}">${t.slice(0, 3)}</div>`;
    });

    // Then one row per attacking type: its label, then 18 cells.
    // Cells that are just 1x are left blank on purpose -- with 324 cells,
    // showing every "1x" would drown out the ones that matter.
    types.forEach(attackingType => {
        const rowColor = TYPE_COLORS[capitalize(attackingType)] || DEFAULT_COLOR;
        html += `<div class="chart-row-label" style="background:${rowColor}">${capitalize(attackingType)}</div>`;
        types.forEach(defendingType => {
            const mult = chart.matchup[attackingType][defendingType] ?? 1;
            html += `<div class="chart-cell ${multiplierClass(mult)}" style="${mult === 1 ? 'background:#bbb' : ''}">${mult === 1 ? '' : formatMultiplier(mult)}</div>`;
        });
    });

    typeChartGridEl.innerHTML = html;
    typeModalOverlay.classList.remove("hidden");
}

function closeTypeChartModal() {
    typeModalOverlay.classList.add("hidden");
}

// ---------------------------------------------------------------
// DESCRIPTION CAROUSEL
// ---------------------------------------------------------------

function renderDescription() {
    const descriptions = currentPokemon.descriptions;

    if (descriptions.length === 0) {
        descriptionVersionEl.textContent = "--";
        descriptionTextEl.textContent = "No description available.";
        document.documentElement.style.setProperty("--version-color", DEFAULT_COLOR);
        return;
    }

    const current = descriptions[currentDescIndex];
    descriptionVersionEl.textContent = current.version;
    descriptionTextEl.textContent = current.text;
    document.documentElement.style.setProperty("--version-color", VERSION_COLORS[current.version] || DEFAULT_COLOR);

    // paging to a Gen II entry should swing the map over to Johto, etc.
    syncMapToDescription();
}

// The two carousel arrows. Every carousel in this file works the same
// way: nudge the index, wrap it around with %, then re-render.
//
// The "+ total" in the backwards one is the trick that stops it going
// negative: in JavaScript, -1 % 5 is -1, not 4. Adding the length first
// keeps the number positive so the wrap-around works.
function showNextDescription() {
    const total = currentPokemon.descriptions.length;
    currentDescIndex = (currentDescIndex + 1) % total;
    renderDescription();
}

function showPrevDescription() {
    const total = currentPokemon.descriptions.length;
    currentDescIndex = (currentDescIndex - 1 + total) % total;
    renderDescription();
}

// ---------------------------------------------------------------
// BIO / EGG PILLS (height, weight, color, habitat, egg groups)
// ---------------------------------------------------------------

function renderBioPills() {
    // The two themes show this data in completely different places: the
    // Pokedex shell splits it between the sprite box and a "Field Survey"
    // slide, while the clean view puts it all in one row of pills. Hence
    // the big if/else.
    const bio = currentPokemon.biological;

    if (document.body.classList.contains("pokedex-theme")) {
        // Render height/weight to sprite box with color pills
        const heightWeightHtml = `
            <span class="pill" style="background: #4fa3e0; color: white;">
                ${RULER_ICON}
                <span>${bio.height} m</span>
            </span>
            <span class="pill" style="background: #d4a017; color: white;">
                ${KETTLEBELL_ICON}
                <span>${bio.weight} kg</span>
            </span>
        `;
        document.getElementById("sprite-height-weight").innerHTML = heightWeightHtml;

        // Render to field survey body with labels (color, habitat, egg groups as text)
        let html = "<div class='field-survey-info'>";

        html += `<div class="field-survey-row">
            <label>Color:</label>
            <span class="field-value">${bio.color || "--"}</span>
        </div>`;

        html += `<div class="field-survey-row">
            <label>Habitat:</label>
            <span class="field-value">${bio.habitat || "--"}</span>
        </div>`;

        if (currentPokemon.egg_groups.length > 0) {
            html += `<div class="field-survey-row">
                <label>Egg Groups:</label>
                <span class="field-value">${currentPokemon.egg_groups.join(", ")}</span>
            </div>`;
        }

        html += "</div>";
        fieldSurveyBodyEl.innerHTML = html;
    } else {
        // Clean view: render as pills
        const pills = [
            { icon: RULER_ICON, text: bio.height + " m" },
            { icon: KETTLEBELL_ICON, text: bio.weight + " kg" },
            { icon: COLOR_ICON, text: bio.color || "--" },
            { icon: HABITAT_ICON, text: bio.habitat || "--" },
            ...currentPokemon.egg_groups.map(group => ({ icon: getEggGroupIcon(group), text: group })),
        ];

        bioPillsRowEl.innerHTML = pills
            .map(p => `<span class="pill">${p.icon}<span>${p.text}</span></span>`)
            .join("");
    }
}

// ---------------------------------------------------------------
// MOVES / TM-HM / FORMS / EVOLUTION SLIDES
// ---------------------------------------------------------------

// The general pattern for every list on the page: take an array, turn
// each item into a string of HTML with .map(), glue them together with
// .join(""), and drop the result into the page in one go. Building the
// string first and assigning once is much faster than adding elements
// one at a time.
function renderMovesSlide() {
    if (currentPokemon.moves.length === 0) {
        movesListEl.innerHTML = "<p>No moves learned by leveling up.</p>";
        return;
    }

    movesListEl.innerHTML = currentPokemon.moves
        .slice(0, 60)  // some pokemon know hundreds; 60 is plenty to show
        .map(move => {
            const color = TYPE_COLORS[move.move_type] || DEFAULT_COLOR;
            const levelLabel = move.learn_method === "Level Up" ? `Lv. ${move.level_learned}` : move.learn_method;
            // Moves inherited from an earlier evolution get a tiny sprite
            // of whoever actually learns them (set by app/main.py).
            const sourceIcon = move.source_sprite
                ? `<img class="move-source-sprite" src="${move.source_sprite}" title="Learned by ${move.source_pokemon_name}">`
                : "";
            return `
                <div class="row-item clickable" data-move="${move.move_name}">
                    <div class="row-left">
                        <span class="type-chip" style="background:${color}">${move.move_type || ""}</span>
                        ${sourceIcon}
                        <span>${move.move_name}</span>
                    </div>
                    <span>${levelLabel}</span>
                </div>
            `;
        })
        .join("");

    attachMoveHandlers(movesListEl);
}

function renderTmHmSlide() {
    if (currentPokemon.tm_hm_moves.length === 0) {
        tmhmListEl.innerHTML = "<p>No TM/HM moves available.</p>";
        return;
    }

    tmhmListEl.innerHTML = currentPokemon.tm_hm_moves
        .map(tm => {
            const color = TYPE_COLORS[tm.move_type] || DEFAULT_COLOR;
            return `
                <div class="row-item clickable" data-move="${tm.move_name}">
                    <div class="row-left">
                        ${vinylIcon(color)}
                        <span>${tm.move_name}</span>
                    </div>
                    <span class="tm-code">${tm.tm_code}</span>
                </div>
            `;
        })
        .join("");

    attachMoveHandlers(tmhmListEl);
}

// Because the lists above are rebuilt as raw HTML, their click handlers
// get wiped every time. So after each render we walk the new rows and
// re-attach. The data-move="..." attribute on each row is how we
// remember which move that row is for.
function attachMoveHandlers(container) {
    container.querySelectorAll("[data-move]").forEach(el => {
        el.addEventListener("click", () => showMoveDetail(el.getAttribute("data-move")));
    });
}

function renderFormsSlide() {
    const forms = currentPokemon.forms;

    if (forms.length === 0) {
        formsListEl.innerHTML = "<p>No alternate forms.</p>";
        return;
    }

    formsListEl.innerHTML = forms
        .map(f => {
            const thumb = f.sprites_available[0] ? f.sprites_available[0].url : "";
            return `
                <div class="form-card" data-variant-id="${f.variant_pokemon_id}">
                    <img src="${thumb}" alt="${f.form_name}">
                    <div class="form-info">
                        <div class="form-name">${f.form_name}</div>
                        <div>${buildTypePillsHtml(f.type1, f.type2)}</div>
                    </div>
                </div>
            `;
        })
        .join("");

    document.querySelectorAll(".form-card").forEach(card => {
        card.addEventListener("click", (event) => {
            if (event.target.closest(".type-pill")) return;
            loadVariant(card.getAttribute("data-variant-id"));
        });
    });
    attachTypePillHandlers(formsListEl);
}

function renderEvolutionSlide() {
    evolutionListEl.innerHTML = buildEvolutionNodeHtml(currentPokemon.evolution);

    evolutionListEl.querySelectorAll("[data-dex]").forEach(el => {
        el.addEventListener("click", () => loadPokemon(el.getAttribute("data-dex")));
    });
}

// Recursively renders one node (as a card) plus the arrow that led into it
// (skipped for the root, which has no parent), plus a row of its children
// underneath -- naturally forms a flow chart, branches and all.
//
// "Recursively" = this function calls itself. Each call draws one pokemon,
// then asks itself to draw each of that pokemon's evolutions, and so on
// until it hits something with no evolutions left. That's why an eight-way
// split like Eevee needs no special handling: it's just a node with eight
// children instead of one.
function buildEvolutionNodeHtml(node) {
    let html = '<div class="evo-node">';

    if (node.trigger_description) {
        html += `
            <div class="evo-arrow">
                <span class="evo-arrow-line">&#8595;</span>
                <span class="evo-arrow-label">${node.trigger_description}</span>
            </div>
        `;
    }

    html += buildEvoCardHtml(node);

    if (node.children.length > 0) {
        html += '<div class="evo-children">';
        html += node.children.map(buildEvolutionNodeHtml).join("");
        html += "</div>";
    }

    html += "</div>";
    return html;
}

function buildEvoCardHtml(node) {
    const classes = ["evo-card"];
    if (node.is_current) classes.push("current");
    if (!node.on_path) classes.push("alternate");

    // green dash badge marks a sibling branch not on this pokemon's own line
    const altBadge = !node.on_path ? '<span class="evo-alt-badge">&#8722;</span>' : "";

    return `
        <div class="${classes.join(" ")}" data-dex="${node.national_dex_no}">
            ${altBadge}
            <img src="${node.sprite || ""}" alt="${node.display_name}">
            <span class="evo-card-name">${node.display_name}</span>
        </div>
    `;
}

// ---------------------------------------------------------------
// MAP SECTION (right column, top) -- generation carousel with pins
// where we have them (Kanto only right now -- see data/maps/README.md)
// ---------------------------------------------------------------

// Ask the server where this pokemon can be caught. The answer comes back
// already grouped into one bucket per (generation, region), because each
// bucket becomes one tab with one map behind it.
async function loadMapData() {
    mapGenTitleEl.textContent = "Loading...";
    const response = await fetch(`/api/pokemon/${currentPokemon.national_dex_no}/encounters`);
    const data = await response.json();
    mapGenerations = data.generations;

    // open on whichever region matches the pokedex entry already showing,
    // rather than always snapping back to the first tab
    const matched = mapIndexForCurrentDescription();
    currentMapGenIndex = matched !== -1 ? matched : 0;
    renderMapSection();
}

// Which map tab corresponds to the description currently on screen? A
// generation can span two regions (HeartGold/SoulSilver cover Johto AND
// Kanto), so this lands on the first tab of that generation. -1 if the
// entry's game has no encounter data at all.
function mapIndexForCurrentDescription() {
    if (!currentPokemon || mapGenerations.length === 0) return -1;
    const desc = currentPokemon.descriptions[currentDescIndex];
    if (!desc || desc.generation_id === null || desc.generation_id === undefined) return -1;
    return mapGenerations.findIndex(g => g.generation_id === desc.generation_id);
}

function syncMapToDescription() {
    const matched = mapIndexForCurrentDescription();
    if (matched !== -1 && matched !== currentMapGenIndex) {
        currentMapGenIndex = matched;
        renderMapSection();
    }
}

// The map image is object-fit:contain, so its drawn rect is letterboxed
// inside #map-image-wrap by an amount that depends on the region's aspect
// ratio (Galar is 240x612, Hoenn is 520x340). Pins are positioned as a %
// of #map-pins, so park that overlay exactly on the drawn artwork.
// naturalWidth/Height on a viewBox-only SVG report a placeholder size but
// a correct ratio, which is all this needs.
function fitMapPins() {
    if (!mapImageEl || !mapPinsEl || !mapImageWrapEl) return;

    const ratio = mapImageEl.naturalWidth / mapImageEl.naturalHeight;
    const box = mapImageWrapEl.getBoundingClientRect();
    if (!ratio || !box.width || !box.height) return;

    const scale = Math.min(box.width / ratio, box.height);
    const width = scale * ratio;

    mapPinsEl.style.width = width + "px";
    mapPinsEl.style.height = scale + "px";
    mapPinsEl.style.left = ((box.width - width) / 2) + "px";
    mapPinsEl.style.top = ((box.height - scale) / 2) + "px";
}

if (mapImageEl) {
    mapImageEl.addEventListener("load", fitMapPins);
}

// panel can change size when the window does, or when a longer location
// list shows up -- keep the overlay glued to the artwork either way
if (mapImageWrapEl && typeof ResizeObserver !== "undefined") {
    new ResizeObserver(fitMapPins).observe(mapImageWrapEl);
}

// Draw the current map tab: the region image, a dot for every location we
// have coordinates for, and the list of location names beside it.
function renderMapSection() {
    if (mapGenerations.length === 0) {
        mapGenTitleEl.textContent = "No Data";
        mapImageWrapEl.classList.add("hidden");
        mapLocationListEl.innerHTML = "<p>Not found in the wild (event/evolution/starter only).</p>";
        return;
    }

    const gen = mapGenerations[currentMapGenIndex];
    mapGenTitleEl.textContent = gen.generation;

    if (gen.map) {
        mapImageWrapEl.classList.remove("hidden");
        mapImageEl.src = `/static/maps/${gen.map}.svg`;
        mapPinsEl.innerHTML = gen.locations
            .map((loc, i) => loc.pin ? `<div class="map-pin" data-loc-index="${i}" style="left:${loc.pin.x}%; top:${loc.pin.y}%" title="${loc.location}"></div>` : "")
            .join("");
        fitMapPins();  // "load" won't fire if we're staying on the same region
    } else {
        mapImageWrapEl.classList.add("hidden");
    }

    mapLocationListEl.innerHTML = gen.locations
        .map((loc, i) => `
            <div class="location-item ${loc.pin ? "pinned" : ""}" data-loc-index="${i}">
                <span class="loc-name">${loc.location}</span>
                <span class="loc-versions">${loc.versions.join(", ")}</span>
            </div>
        `)
        .join("");

    mapLocationListEl.querySelectorAll(".location-item.pinned").forEach(item => {
        item.addEventListener("click", () => highlightMapPin(item.getAttribute("data-loc-index")));
    });
    mapPinsEl.querySelectorAll(".map-pin").forEach(pin => {
        pin.addEventListener("click", () => highlightMapPin(pin.getAttribute("data-loc-index")));
    });
}

// Clicking either a dot on the map or a name in the list highlights both,
// so you can see which is which. Clear every highlight first, then set the
// one we want.
function highlightMapPin(index) {
    document.querySelectorAll(".map-pin").forEach(p => p.classList.remove("highlighted"));
    document.querySelectorAll(".location-item").forEach(p => p.classList.remove("highlighted"));

    const pin = mapPinsEl.querySelector(`[data-loc-index="${index}"]`);
    if (pin) pin.classList.add("highlighted");

    const item = mapLocationListEl.querySelector(`[data-loc-index="${index}"]`);
    if (item) item.classList.add("highlighted");
}

function showNextMapGen() {
    if (mapGenerations.length === 0) return;
    currentMapGenIndex = (currentMapGenIndex + 1) % mapGenerations.length;
    renderMapSection();
}

function showPrevMapGen() {
    if (mapGenerations.length === 0) return;
    currentMapGenIndex = (currentMapGenIndex - 1 + mapGenerations.length) % mapGenerations.length;
    renderMapSection();
}

// ---------------------------------------------------------------
// SPRITE / DATA CAROUSELS
// ---------------------------------------------------------------

function showNextSprite() {
    const source = currentVariant !== null ? currentVariant : currentPokemon;
    currentSpriteIndex = (currentSpriteIndex + 1) % source.sprites_available.length;
    renderSprite();
}

function showPrevSprite() {
    const source = currentVariant !== null ? currentVariant : currentPokemon;
    const total = source.sprites_available.length;
    currentSpriteIndex = (currentSpriteIndex - 1 + total) % total;
    renderSprite();
}

function renderCarouselPosition() {
    slides.forEach(slide => document.getElementById(slide.id).classList.remove("active"));
    const current = slides[currentSlideIndex];
    document.getElementById(current.id).classList.add("active");
    carouselTitleEl.textContent = current.title;
}

function showNextSlide() {
    currentSlideIndex = (currentSlideIndex + 1) % slides.length;
    renderCarouselPosition();
}

function showPrevSlide() {
    currentSlideIndex = (currentSlideIndex - 1 + slides.length) % slides.length;
    renderCarouselPosition();
}

// ---------------------------------------------------------------
// FLIP BUTTONS
// ---------------------------------------------------------------

// Step one dex number forward or back. Math.min/max stop you falling off
// either end -- unlike the carousels, these deliberately don't wrap.
function flipToNext() {
    loadPokemon(Math.min(currentPokemon.national_dex_no + 1, maxDexNo));
}

function flipToPrev() {
    loadPokemon(Math.max(currentPokemon.national_dex_no - 1, minDexNo));
}

// ---------------------------------------------------------------
// TYPEAHEAD SEARCH
// ---------------------------------------------------------------

async function runSearch(query) {
    if (query.trim().length === 0) {
        searchSuggestionsEl.innerHTML = "";
        return;
    }
    const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
    renderSuggestions(await response.json());
}

function renderSuggestions(results) {
    if (results.length === 0) {
        searchSuggestionsEl.innerHTML = "";
        return;
    }

    searchSuggestionsEl.innerHTML = results
        .map(r => `
            <div class="suggestion-item" data-dex-no="${r.national_dex_no}">
                <span>${r.display_name}</span>
                <span>#${String(r.national_dex_no).padStart(3, "0")}</span>
            </div>
        `)
        .join("");

    document.querySelectorAll(".suggestion-item").forEach(item => {
        item.addEventListener("click", () => {
            loadPokemon(item.getAttribute("data-dex-no"));
            searchInput.value = "";
            searchSuggestionsEl.innerHTML = "";
        });
    });
}

// ---------------------------------------------------------------
// COLLAPSIBLE SECTIONS (static headers, wired once)
// ---------------------------------------------------------------

document.querySelectorAll(".section-header:not(.no-collapse)").forEach(header => {
    header.addEventListener("click", () => {
        header.classList.toggle("collapsed");
        header.nextElementSibling.classList.toggle("collapsed");
    });
});

// ---------------------------------------------------------------
// EVENT LISTENERS
// ---------------------------------------------------------------

// Search as you type -- but not on EVERY keystroke. "Debouncing": each
// keypress cancels the previous pending search and starts a fresh 250ms
// timer, so typing "charizard" fires one request when you stop, not nine
// while you type.
if (searchInput) {
    searchInput.addEventListener("input", () => {
        clearTimeout(searchDebounceTimer);
        searchDebounceTimer = setTimeout(() => runSearch(searchInput.value), 250);
    });
}

// Click anywhere outside a search box and its dropdown disappears.
// .closest() walks up from whatever you clicked looking for that
// wrapper -- if it doesn't find one, the click was outside.
document.addEventListener("click", (event) => {
    if (!event.target.closest("#search-wrapper")) {
        searchSuggestionsEl.innerHTML = "";
    }
    if (!event.target.closest("#shell-search-wrap")) {
        if (shellSearchSuggestionsEl) shellSearchSuggestionsEl.innerHTML = "";
    }
});

// Typeahead for the shell name input in pokedex view -- searches by name OR
// dex number, same dropdown pattern as the clean view's search bar.
if (shellNameInput && shellSearchSuggestionsEl) {
    let shellSearchDebounceTimer = null;
    let shellSearchResults = [];

    async function runShellSearch(query) {
        if (query.trim().length === 0) {
            shellSearchSuggestionsEl.innerHTML = "";
            shellSearchResults = [];
            return;
        }
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        shellSearchResults = await response.json();
        renderShellSuggestions(shellSearchResults);
    }

    function renderShellSuggestions(results) {
        if (results.length === 0) {
            shellSearchSuggestionsEl.innerHTML = "";
            return;
        }

        shellSearchSuggestionsEl.innerHTML = results
            .map(r => `
                <div class="suggestion-item" data-dex-no="${r.national_dex_no}">
                    <span>${r.display_name}</span>
                    <span>#${String(r.national_dex_no).padStart(3, "0")}</span>
                </div>
            `)
            .join("");

        shellSearchSuggestionsEl.querySelectorAll(".suggestion-item").forEach(item => {
            item.addEventListener("click", () => {
                loadPokemon(item.getAttribute("data-dex-no"));
                shellSearchSuggestionsEl.innerHTML = "";
            });
        });
    }

    shellNameInput.addEventListener("input", () => {
        clearTimeout(shellSearchDebounceTimer);
        shellSearchDebounceTimer = setTimeout(() => runShellSearch(shellNameInput.value), 200);
    });

    shellNameInput.addEventListener("focus", () => {
        shellNameInput.select();
    });

    shellNameInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && shellSearchResults.length > 0) {
            loadPokemon(shellSearchResults[0].national_dex_no);
            shellSearchSuggestionsEl.innerHTML = "";
        }
    });
}

// Every button gets wired up here. The `if (...)` guard on each line is
// because both themes share this file, and a button that only exists in
// one of them would otherwise be null and throw an error on the other.
if (flipPrevBtn) flipPrevBtn.addEventListener("click", flipToPrev);
if (flipNextBtn) flipNextBtn.addEventListener("click", flipToNext);

if (shellNavPrevBtn) shellNavPrevBtn.addEventListener("click", flipToPrev);
if (shellNavNextBtn) shellNavNextBtn.addEventListener("click", flipToNext);

if (backToBaseBtn) backToBaseBtn.addEventListener("click", clearVariant);

if (spritePrevBtn) spritePrevBtn.addEventListener("click", showPrevSprite);
if (spriteNextBtn) spriteNextBtn.addEventListener("click", showNextSprite);

if (descPrevBtn) descPrevBtn.addEventListener("click", showPrevDescription);
if (descNextBtn) descNextBtn.addEventListener("click", showNextDescription);

if (mapGenPrevBtn) mapGenPrevBtn.addEventListener("click", showPrevMapGen);
if (mapGenNextBtn) mapGenNextBtn.addEventListener("click", showNextMapGen);

if (carouselPrevBtn) carouselPrevBtn.addEventListener("click", showPrevSlide);
if (carouselNextBtn) carouselNextBtn.addEventListener("click", showNextSlide);

// Type chart modal markup only exists on the clean view right now --
// the Pokedex shell pulled it out until it has a place to live there.
if (typeModalClose && typeModalOverlay) {
    typeModalClose.addEventListener("click", closeTypeChartModal);
    typeModalOverlay.addEventListener("click", (event) => {
        if (event.target === typeModalOverlay) closeTypeChartModal();
    });
}

if (assetPopoverClose) assetPopoverClose.addEventListener("click", closeAssetPopover);
if (assetPopoverOverlay) assetPopoverOverlay.addEventListener("click", (event) => {
    if (event.target === assetPopoverOverlay) closeAssetPopover();
});

// ---------------------------------------------------------------
// INITIAL LOAD
//
// Everything above was setup. This one line is what kicks the app off:
// fetch the metadata first (we need the stat ranges before we can draw a
// stat bar), and only THEN load a pokemon. #6 is Charizard, the default
// starting page.
// ---------------------------------------------------------------
loadMeta().then(() => loadPokemon(6));
