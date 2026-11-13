// When switched on, rewrites the page's text with every spelling rule (and the
// very common words). Original text is kept so switching off restores it.
(() => {
  "use strict";
  const { respellText } = self.SimpleSpelling;

  const SKIP = "script, style, noscript, textarea, input, select, code, pre, kbd, samp, [contenteditable=''], [contenteditable='true']";
  const original = new WeakMap();   // text node -> its original text
  const written = new WeakMap();    // text node -> the text we last wrote
  let table = null;
  let on = false;
  let allLevels = new Set();        // every level number, once the table loads

  function skipped(node) {
    const el = node.parentElement;
    return !el || el.closest(SKIP) !== null;
  }

  function sentenceStartFor(node, prevText) {
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
    const out = on ? respellText(table, src, allLevels, sentenceStartFor(node, prevText), true)
      : src;
    if (node.nodeValue !== out) node.nodeValue = out;
    written.set(node, out);
    return src;
  }

  function renderTree(root) {
    if (!table) return;
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

  async function start() {
    const res = await fetch(chrome.runtime.getURL("respellings.json"));
    table = await res.json();
    allLevels = new Set(table.levels.map((_, i) => i + 1));
    on = (await chrome.storage.sync.get({ on: false })).on;
    renderTree(document.body);
    observer.observe(document.body, { childList: true, subtree: true, characterData: true });
  }

  chrome.storage.onChanged.addListener((changes) => {
    if (changes.on) {
      on = changes.on.newValue;
      renderTree(document.body);
    }
  });

  start();
})();
