import { state } from "../state/GameState.js";
import { crew } from "../config.js";
import { button, paragraph, showModal, modal } from "./DialogueUI.js";
export function renderProgress() {
  const root = document.querySelector("#progress");
  root.replaceChildren();
  const head = document.createElement("div");
  head.className = "profile";
  head.innerHTML =
    '<div class="avatar">◉</div><div><small>YOUR EXPEDITION</small><h3>Cadet Explorer</h3><span>Learning by discovery</span></div>';
  root.append(head);
  const stats = document.createElement("div");
  stats.className = "stats";
  stats.innerHTML = `<div><strong>${state.data.xp}</strong><small>TOTAL XP</small></div><div><strong>${state.data.completed.length}<em> / 3</em></strong><small>SYSTEMS RESTORED</small></div>`;
  root.append(stats, paragraph("MISSION LOG", "eyebrow"));
  const titles = [
    "Unstick the rover",
    "Power the outpost",
    "Grow a greener Mars",
  ];
  crew.forEach((c, i) => {
    const done = state.data.completed.includes(c.mission);
    const b = button(
      "",
      () =>
        window.dispatchEvent(
          new CustomEvent("navigate-crew", { detail: c.id }),
        ),
      "mission",
    );
    const number = document.createElement("span");
    number.className = done ? "mission-number done" : "mission-number";
    number.textContent = done ? "✓" : `0${i + 1}`;
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = titles[i];
    const sub = document.createElement("small");
    sub.textContent = `${["PHYSICS", "ENERGY", "BIOLOGY"][i]} · ${done ? "COMPLETE" : "100 XP"}`;
    copy.append(title, sub);
    b.append(number, copy);
    root.append(b);
  });
  root.append(paragraph("SUBJECT MASTERY", "eyebrow"));
  crew.forEach((c, i) => {
    const line = document.createElement("div");
    line.className = "mastery";
    const val = Math.round((state.data.mastery[c.mission] || 0) * 100);
    line.innerHTML = `<div><span>${["Forces & motion", "Electrical energy", "Plant biology"][i]}</span><span>${val}%</span></div><progress max="100" value="${val}" aria-label="${c.role} subject mastery"></progress>`;
    root.append(line);
  });
  const note = document.createElement("div");
  note.className = "field-note";
  note.append(
    paragraph(
      state.data.completed.length === 3
        ? "✧ Colony restored!"
        : "✧ A little curiosity goes a long way.",
      "note-title",
    ),
    paragraph(
      state.data.completed.length === 3
        ? "All three systems are online. Revisit your crew to review what you learned."
        : "Talk to your crew. Each mission turns a science idea into something you can use.",
    ),
  );
  root.append(note);
  root.append(
    button(
      "How to explore ↗",
      () => {
        showModal("Your first day on Mars", "FIELD MANUAL");
        modal.append(
          paragraph(
            "Move with WASD or the arrow keys. Walk near a crewmate and press E, or click a crewmate or mission to walk there automatically.",
          ),
          paragraph(
            "Ask for an explanation, solve the challenge, and use up to three hints. Correct answers restore colony systems. Hints reduce the XP reward, but you can retry freely.",
          ),
          paragraph(
            "Your progress is saved in this browser. Offline mode uses authored lessons. Live AI mode connects to your configured backend for generated dialogue, explanations, and hints.",
          ),
        );
      },
      "help",
    ),
  );
}
