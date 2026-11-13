// Pure respelling logic, shared by the content script, the popup and the tests.
//
// `table` is respellings.json:
//   levels: [{ id, name, examples }]            level numbers are 1-based indexes
//   common: { word: spelling }                   the very common words (to, do, you…)
//   words:  { word: { c: [chunks], e: [[level, chunkIndex, text], …] } }
// Each edit replaces one letter chunk; chunkIndex -1 replaces the whole word.

(function (root) {
  "use strict";

  /**
   * Spelling of a lowercase word with the given levels switched on, or null
   * if it doesn't change. `enabled` is a Set of level numbers; with `common`,
   * the very common words (to, do, you…) are respelled too.
   */
  function spellingFor(table, lower, enabled, common = false) {
    // Object.hasOwn, not table.words[lower]: words like "constructor" and
    // "toString" would otherwise find JavaScript's built-in properties.
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

  const WORD = /[A-Za-z]+/g;

  /**
   * Respell every known word in `text`. A capitalised word that isn't at the
   * start of a sentence is treated as a name and left alone (Chicago, Phil).
   * `atSentenceStart` says whether `text` itself begins a sentence.
   */
  function respellText(table, text, enabled, atSentenceStart, common = false) {
    if (enabled.size === 0 && !common) return text;
    return text.replace(WORD, (word, offset) => {
      const lower = word.toLowerCase();
      const sp = spellingFor(table, lower, enabled, common);
      if (!sp) return word;
      const capitalised = word[0] !== lower[0];
      const allCaps = word.length > 1 && word === word.toUpperCase();
      if (capitalised && !allCaps) {
        const before = text.slice(0, offset);
        const sentenceStart = /[.!?:"“(]\s*$/.test(before) ||
          (atSentenceStart && /^\s*$/.test(before));
        if (!sentenceStart) return word;
      }
      return matchCase(word, sp);
    });
  }

  const api = { spellingFor, matchCase, respellText };
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  } else {
    root.SimpleSpelling = api;
  }
})(typeof self !== "undefined" ? self : this);
