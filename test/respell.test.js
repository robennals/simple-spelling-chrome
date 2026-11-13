const test = require("node:test");
const assert = require("node:assert");
const path = require("node:path");
const { spellingFor, respellText } = require("../extension/respell.js");
const table = require(path.join(__dirname, "../extension/respellings.json"));

const ALL = new Set(table.levels.map((_, i) => i + 1));
const NONE = new Set();
// Level numbers for the given level ids, to test one rule at a time.
const only = (...ids) => new Set(ids.map((id) => table.levels.findIndex((l) => l.id === id) + 1));

test("a level's change appears only when that level is applied", () => {
  assert.strictEqual(spellingFor(table, "though", NONE), null);
  assert.strictEqual(spellingFor(table, "though", only("ough")), "tho");
  assert.strictEqual(spellingFor(table, "though", only("igh")), null);
});

test("levels apply independently of each other", () => {
  // ready: the ea level changes two chunks (ea -> e, d -> dd)
  assert.strictEqual(spellingFor(table, "ready", only("ea")), "reddy");
  // what: wh and wa each change their own chunk
  assert.strictEqual(spellingFor(table, "what", only("wh")), "wat");
  assert.strictEqual(spellingFor(table, "what", only("wa")), "whot");
  assert.strictEqual(spellingFor(table, "what", only("wa", "wh")), "wot");
});

test("hand-picked words replace the whole word", () => {
  assert.strictEqual(spellingFor(table, "could", only("sight")), "cud");
  assert.strictEqual(spellingFor(table, "could", ALL), "cud");
});

test("with no levels, text is untouched", () => {
  const s = "Though the night was long, we said nothing.";
  assert.strictEqual(respellText(table, s, NONE, true), s);
});

test("respells a sentence with everything on, keeping case and punctuation", () => {
  assert.strictEqual(
    respellText(table, "Though the night was long, we said nothing.", ALL, true),
    "Tho the nite wos long, we sed nuthing.",
  );
});

test("ALL CAPS stays all caps", () => {
  assert.strictEqual(respellText(table, "NIGHT", ALL, true), "NITE");
});

test("capitalised words mid-sentence are treated as names", () => {
  // "Phil" and "Knight" would otherwise become "Fil" and "Nite".
  assert.strictEqual(respellText(table, "we met Phil Knight", ALL, false), "we met Phil Knight");
  assert.strictEqual(respellText(table, "a phone. Phone me", ALL, false), "a fone. Fone me");
});

test("contractions keep their apostrophe", () => {
  assert.strictEqual(respellText(table, "I couldn't", ALL, true), "I cudn't");
});

test("common words change only when that option is on", () => {
  const s = "you need to do it";
  assert.strictEqual(respellText(table, s, ALL, true, false), s);
  assert.strictEqual(respellText(table, s, ALL, true, true), "yoo need too doo it");
  assert.strictEqual(respellText(table, s, NONE, true, true), "yoo need too doo it");
});

test("words that are JavaScript property names are left alone", () => {
  const s = "call the constructor or toString or hasOwnProperty";
  assert.strictEqual(respellText(table, s, ALL, true, true), s);
});
