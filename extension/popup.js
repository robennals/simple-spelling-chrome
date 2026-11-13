// Mode picker (Off / Simple fixes / Fully phonetic), saved in
// chrome.storage.sync (the content script listens to it), plus a reference
// list for the chosen mode: the simple-fix rules, or the phonetic key.
(async () => {
  "use strict";
  const load = async (file) => (await fetch(chrome.runtime.getURL(file))).json();
  const [simple, phonetic] = await Promise.all([load("respellings.json"), load("phonetic.json")]);
  const blurb = document.getElementById("blurb");
  const BLURBS = {
    off: "Pages show normal spelling.",
    simple: "Fixes the most confusing spellings, using familiar casual spellings.",
    phonetic: "Every sound is written one way. British and American vowels that differ get different spellings.",
  };

  const rules = document.getElementById("rules");
  const common = Object.entries(simple.common).slice(0, 5).map(([w, sp]) => `${w} → ${sp}`).join(", ");
  for (const rule of [{ name: "Very common words", examples: common }, ...simple.levels]) {
    const li = document.createElement("li");
    li.textContent = rule.name;
    const ex = document.createElement("span");
    ex.className = "ex";
    ex.textContent = rule.examples;
    li.appendChild(ex);
    rules.appendChild(li);
  }

  const key = document.getElementById("key");
  for (const row of phonetic.key) {
    const tr = key.insertRow();
    tr.insertCell().textContent = row.sound;
    const sp = tr.insertCell();
    sp.className = "sp";
    sp.textContent = row.spelling;
    const ex = tr.insertCell();
    ex.className = "ex";
    ex.textContent = row.examples;
  }

  const radios = [...document.querySelectorAll("input[name=mode]")];
  function show(mode) {
    radios.forEach((r) => { r.checked = r.value === mode; });
    blurb.textContent = BLURBS[mode];
    document.getElementById("simple").hidden = mode !== "simple";
    document.getElementById("phonetic").hidden = mode !== "phonetic";
  }

  // Older versions stored a single on/off switch.
  const stored = await chrome.storage.sync.get({ mode: null, on: false });
  show(stored.mode || (stored.on ? "simple" : "off"));
  radios.forEach((r) => r.addEventListener("change", () => {
    show(r.value);
    chrome.storage.sync.set({ mode: r.value });
  }));
})();
