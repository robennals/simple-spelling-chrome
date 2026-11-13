const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const {
  spellingFor, simpleLookup, phoneticLookup, respellText,
} = require("../extension/respell.js");
const simple = require(path.join(__dirname, "../extension/respellings.json"));
const phonetic = require(path.join(__dirname, "../extension/phonetic.json"));

const NONE = new Set();
// Level numbers for the given level ids, to test one rule at a time.
const only = (...ids) => new Set(ids.map((id) => simple.levels.findIndex((l) => l.id === id) + 1));
const SIMPLE = simpleLookup(simple);
const PHONETIC = phoneticLookup(phonetic);

// --- Simple fixes: levels ------------------------------------------------

test("a level's change appears only when that level is applied", () => {
  assert.strictEqual(spellingFor(simple, "though", NONE), null);
  assert.strictEqual(spellingFor(simple, "though", only("ough")), "tho");
  assert.strictEqual(spellingFor(simple, "though", only("igh")), null);
});

test("levels apply independently of each other", () => {
  // ready: the ea level changes two chunks (ea -> e, d -> dd)
  assert.strictEqual(spellingFor(simple, "ready", only("ea")), "reddy");
  // what: wh and wa each change their own chunk
  assert.strictEqual(spellingFor(simple, "what", only("wh")), "wat");
  assert.strictEqual(spellingFor(simple, "what", only("wa")), "whot");
  assert.strictEqual(spellingFor(simple, "what", only("wa", "wh")), "wot");
});

test("hand-picked words replace the whole word", () => {
  assert.strictEqual(spellingFor(simple, "could", only("sight")), "cud");
});

test("very common words change only with that option", () => {
  assert.strictEqual(spellingFor(simple, "you", only("sight"), false), null);
  assert.strictEqual(spellingFor(simple, "you", NONE, true), "yoo");
});

// --- Simple fixes: whole text --------------------------------------------

test("respells a sentence, keeping case and punctuation", () => {
  assert.strictEqual(
    respellText("Though the night was long, we said nothing.", SIMPLE, true),
    "Tho the nite wos long, we sed nuthing.",
  );
  assert.strictEqual(respellText("you need to do it", SIMPLE, true), "yoo need too doo it");
});

test("ALL CAPS stays all caps", () => {
  assert.strictEqual(respellText("NIGHT", SIMPLE, true), "NITE");
});

test("capitalised words mid-sentence are treated as names", () => {
  // "Phil" and "Knight" would otherwise become "Fil" and "Nite".
  assert.strictEqual(respellText("we met Phil Knight", SIMPLE, false), "we met Phil Knight");
  assert.strictEqual(respellText("a phone. Phone me", SIMPLE, false), "a fone. Fone me");
});

test("contractions not in the table are respelled part by part", () => {
  assert.strictEqual(respellText("I couldn't", SIMPLE, true), "I cudn't");
  assert.strictEqual(respellText("I couldn’t", SIMPLE, true), "I cudn’t");
});

test("JavaScript property names never leak into the text", () => {
  const s = "call toString or hasOwnProperty or valueOf";
  assert.strictEqual(respellText(s, SIMPLE, true), s);
  assert.strictEqual(respellText(s, PHONETIC, true).split(" ").filter((w, i) => i % 2 === 1).join(" "),
    "toString hasOwnProperty valueOf");
  // "constructor" is a real word: it gets a real spelling, not Object's constructor
  assert.match(respellText("constructor", PHONETIC, true), /^[a-z]+$/);
});

// --- Fully phonetic ------------------------------------------------------

test("fully phonetic respells every word by sound", () => {
  assert.strictEqual(
    respellText("I thought we should go out tonight.", PHONETIC, true),
    "Iy thawt wee shood goh owt taniyt.",
  );
});

test("fully phonetic keeps British/American vowel differences apart", () => {
  const ph = (w) => PHONETIC(w) ?? w;           // unchanged words aren't stored
  assert.strictEqual(ph("bath"), "bahth");     // British "ah", American "a"
  assert.strictEqual(ph("father"), "faather"); // palm
  assert.strictEqual(ph("hot"), "hot");        // lot
  assert.strictEqual(ph("thought"), "thawt");  // thought
  assert.strictEqual(ph("car"), "kaar");       // r is kept
  assert.strictEqual(ph("new"), "nyuu");       // British y is kept
});

test("I stays capitalised mid-sentence and contractions are looked up whole", () => {
  assert.strictEqual(respellText("so I can't go", PHONETIC, false), "soh Iy kant goh");
  assert.strictEqual(respellText("so I can’t go", PHONETIC, false), "soh Iy kant goh");
});

test("abbreviations are left alone in both modes", () => {
  const s = "St Paul met Mr Smith and Dr Jones from the FBI, etc.";
  assert.strictEqual(respellText(s, SIMPLE, true), s);
  assert.strictEqual(respellText("st Paul, mr Smith, dr Jones, the fbi, etc.", PHONETIC, true),
    "st Paul, mr Smith, dr Jones, tha fbi, etc.");
});

test("fully phonetic builds word forms missing from the table from their base word", () => {
  // exhales / exhaled / exhaling aren't in the table, but exhale is
  assert.strictEqual(PHONETIC("exhales"), PHONETIC("exhale") + "z");
  assert.strictEqual(PHONETIC("exhaled"), PHONETIC("exhale") + "d");
  assert.strictEqual(PHONETIC("exhaling"), PHONETIC("exhale") + "ing");
  // known unchanged words are never rebuilt from a shorter word
  assert.strictEqual(PHONETIC("need"), null);
  // unknown words with no known base stay unknown
  assert.strictEqual(PHONETIC("blorfs"), null);
});
