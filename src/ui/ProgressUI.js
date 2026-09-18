import { state } from "../state/GameState.js";
import { levels } from "../config.js";

let activeLevel = 0;

window.addEventListener("realm-changed", (event) => {
  activeLevel = event.detail;
  renderProgress();
});

export function renderProgress() {
  const root = document.querySelector("#level-hud");
  if (!root) return;
  root.replaceChildren();

  const level = levels[activeLevel] || levels[0];
  const identity = document.createElement("div");
  identity.className = "hud-identity";
  identity.innerHTML = `<span class="hud-glyph">${level.constellation}</span><span><small>WORLD ${activeLevel + 1} / ${levels.length}</small><strong>${level.title}</strong><em>${level.objective}</em></span>`;

  const path = document.createElement("div");
  path.className = "realm-path";
  path.setAttribute(
    "aria-label",
    `${state.data.completed.length} of ${levels.length} levels complete`,
  );
  levels.forEach((item, index) => {
    const node = document.createElement("span");
    const complete = state.data.completed.includes(item.mission);
    node.className = `realm-node${complete ? " complete" : ""}${index === activeLevel ? " active" : ""}`;
    node.textContent = complete ? "✓" : index + 1;
    node.title = complete ? `${item.title} complete` : item.title;
    path.append(node);
    if (index < levels.length - 1) path.append(document.createElement("i"));
  });

  const score = document.createElement("div");
  score.className = "hud-score";
  score.innerHTML = `<strong>${state.data.xp}</strong><small>XP</small>`;
  root.append(identity, path, score);
}
