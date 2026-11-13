// Rewrites the page's text in the chosen mode ("simple" fixes or fully
// "phonetic"), and re-renders when the mode changes. Original text is kept so
// switching off restores it.
(() => {
  "use strict";
  const { respellText, simpleLookup, phoneticLookup } = self.SimpleSpelling;

  const SKIP = "script, style, noscript, textarea, input, select, code, pre, kbd, samp, [contenteditable=''], [contenteditable='true']";
  const TABLES = { simple: "respellings.json", phonetic: "phonetic.json" };
  const MAKE_LOOKUP = { simple: simpleLookup, phonetic: phoneticLookup };
  const original = new WeakMap();   // text node -> its original text
  const written = new WeakMap();    // text node -> the text we last wrote
  const lookups = {};               // mode -> lookup function, loaded on first use
  let mode = "off";

  function skipped(node) {
    const el = node.parentElement;
    return !el || el.closest(SKIP) !== null;
  }

  function sentenceStartFor(prevText) {
    // A text node starts a sentence if nothing precedes it in its block or
    // the preceding text ends a sentence.
    if (prevText === null) return true;
    return /[.!?:"“]\s*$/.test(prevText) || /^\s*$/.test(prevText);
  }

  function renderNode(node, prevText) {
    if (written.has(node) && node.nodeValue !== written.get(node)) {
      original.set(node, node.nodeValue);   // the page changed it
    }
    if (!original.has(node)) original.set(node, node.nodeValue);
    const src = original.get(node);
    const lookup = lookups[mode];
    const out = lookup ? respellText(src, lookup, sentenceStartFor(prevText)) : src;
    if (node.nodeValue !== out) node.nodeValue = out;
    written.set(node, out);
    return src;
  }

  function renderTree(root) {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: (n) => (skipped(n) || !/[A-Za-z]/.test(n.nodeValue)
        ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT),
    });
    let prev = null;
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      try {
        prev = renderNode(n, prev);
      } catch (e) {
        // one bad piece of text shouldn't stop the rest of the page
        console.error("Simple Spelling: couldn't respell", JSON.stringify(n.nodeValue), e);
      }
    }
  }

  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "characterData") {
        const n = m.target;
        if (written.get(n) !== n.nodeValue && !skipped(n)) renderNode(n, null);
      } else {
        for (const n of m.addedNodes) {
          if (n.nodeType === Node.TEXT_NODE) {
            if (!skipped(n)) renderNode(n, null);
          } else if (n.nodeType === Node.ELEMENT_NODE) {
            renderTree(n);
          }
        }
      }
    }
  });

  async function setMode(next) {
    if (TABLES[next] && !lookups[next]) {
      const res = await fetch(chrome.runtime.getURL(TABLES[next]));
      lookups[next] = MAKE_LOOKUP[next](await res.json());
    }
    mode = next;
    renderTree(document.body);
  }

  chrome.storage.onChanged.addListener((changes) => {
    if (changes.mode) setMode(changes.mode.newValue || "off");
  });

  (async () => {
    // Older versions stored a single on/off switch.
    const stored = await chrome.storage.sync.get({ mode: null, on: false });
    await setMode(stored.mode || (stored.on ? "simple" : "off"));
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  })();
})();
