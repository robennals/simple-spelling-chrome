// Pure respelling logic, shared by the content script, the popup and the tests.
//
// Two tables:
//   respellings.json (simple fixes)
//     levels: [{ id, name, examples }]       level numbers are 1-based indexes
//     common: { word: spelling }              the very common words (to, do, you…)
//     words:  { word: { c: [chunks], e: [[level, chunkIndex, text], …] } }
//     Each edit replaces one letter chunk; chunkIndex -1 replaces the whole word.
//   phonetic.json (fully phonetic)
//     key:   [{ sound, spelling, examples }]
//     words: { word: spelling }
//
// Lookups use Object.hasOwn, not table[word]: words like "constructor" and
// "toString" would otherwise find JavaScript's built-in properties.

(function (root) {
  "use strict";

  /**
   * Simple-fixes spelling of a lowercase word with the given levels on, or
   * null if it doesn't change. `enabled` is a Set of level numbers; with
   * `common`, the very common words (to, do, you…) are respelled too.
   */
  function spellingFor(table, lower, enabled, common = false) {
    if (common && table.common && Object.hasOwn(table.common, lower)) return table.common[lower];
    if (!Object.hasOwn(table.words, lower)) return null;
    const entry = table.words[lower];
    let whole = null;
    let chunks = null;
    for (const [level, index, text] of entry.e) {
      if (!enabled.has(level)) continue;
      if (index === -1) {
        whole = text;
      } else {
        chunks = chunks || entry.c.slice();
        chunks[index] = text;
      }
    }
    if (whole !== null) return whole;
    return chunks ? chunks.join("") : null;
  }

  /** Lookup for "Simple fixes": every level plus the very common words. */
  function simpleLookup(table) {
    const all = new Set(table.levels.map((_, i) => i + 1));
    return (lower) => spellingFor(table, lower, all, true);
  }

  /** Lookup for "Fully phonetic". */
  function phoneticLookup(table) {
    return (lower) => (Object.hasOwn(table.words, lower) ? table.words[lower] : null);
  }

  /** Copy the capitalisation pattern of `original` onto `replacement`. */
  function matchCase(original, replacement) {
    if (original.length > 1 && original === original.toUpperCase()) {
      return replacement.toUpperCase();
    }
    if (original[0] === original[0].toUpperCase()) {
      return replacement[0].toUpperCase() + replacement.slice(1);
    }
    return replacement;
  }

  // A word, including contractions like can't / don’t.
  const WORD = /[A-Za-z]+(?:['’][A-Za-z]+)*/g;
  const PART = /[A-Za-z]+/g;

  /**
   * Respell every known word in `text` using `lookup(lowercaseWord)`, which
   * returns a spelling or null. A capitalised word that isn't at the start of
   * a sentence is treated as a name and left alone (Chicago, Phil), except I.
   * `atSentenceStart` says whether `text` itself begins a sentence.
   * Contractions are looked up whole (can't), then part by part.
   */
  function respellText(text, lookup, atSentenceStart) {
    function isName(word, offset) {
      const lower = word.toLowerCase();
      if (lower === "i" || lower.startsWith("i'") || lower.startsWith("i’")) return false;
      const capitalised = word[0] !== lower[0];
      const allCaps = word.length > 1 && word === word.toUpperCase();
      if (!capitalised || allCaps) return false;
      const before = text.slice(0, offset);
      const sentenceStart = /[.!?:"“(]\s*$/.test(before) ||
        (atSentenceStart && /^\s*$/.test(before));
      return !sentenceStart;
    }
    function one(word, offset) {
      const sp = lookup(word.toLowerCase().replace(/’/g, "'"));
      if (!sp || isName(word, offset)) return null;
      return matchCase(word, sp);
    }
    return text.replace(WORD, (word, offset) => {
      const whole = one(word, offset);
      if (whole !== null) return whole;
      if (!/['’]/.test(word)) return word;
      return word.replace(PART, (part, i) => one(part, offset + i) ?? part);
    });
  }

  const api = { spellingFor, simpleLookup, phoneticLookup, matchCase, respellText };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.SimpleSpelling = api;
  }
})(typeof self !== "undefined" ? self : this);
