// One on/off toggle, saved in chrome.storage.sync (the content script listens
// to it), and a read-only list of the spelling rules it applies.
(async () => {
  "use strict";
  const table = await (await fetch(chrome.runtime.getURL("respellings.json"))).json();
  const toggle = document.getElementById("on");
  const state = document.getElementById("state");
  const list = document.getElementById("rules");

  const common = Object.entries(table.common).slice(0, 5)
    .map(([w, sp]) => `${w} → ${sp}`).join(", ");
  const rules = [{ name: "Very common words", examples: common }, ...table.levels];
  for (const rule of rules) {
    const li = document.createElement("li");
    li.textContent = rule.name;
    const ex = document.createElement("span");
    ex.className = "ex";
    ex.textContent = rule.examples;
    li.appendChild(ex);
    list.appendChild(li);
  }

  function show(on) {
    toggle.checked = on;
    state.textContent = on ? "On" : "Off";
    document.body.classList.toggle("off", !on);
  }

  const { on } = await chrome.storage.sync.get({ on: false });
  show(on);
  toggle.addEventListener("change", () => {
    show(toggle.checked);
    chrome.storage.sync.set({ on: toggle.checked });
  });
})();
