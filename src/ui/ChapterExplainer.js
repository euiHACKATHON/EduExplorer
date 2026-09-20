import { api } from "../api/APIService.js";
import { levels } from "../config.js";
import { openAnimatedMission } from "./AnimatedMission.js";
import { openScienceArcade } from "./ScienceArcade.js";
import {
  button,
  modal,
  paragraph,
  showModal,
  modalRevision,
  isCurrentModal,
} from "./DialogueUI.js";

async function chooseFormat(mission, format) {
  showModal("Preparing your expedition…", "LEARNING STUDIO");
  const token = modalRevision();
  let content;
  try {
    content = await api.generateExperience(mission, format);
  } catch {
    /* Authored scenes remain available. */
  }
  if (!isCurrentModal(token)) return;
  if (format === "mini_game") openScienceArcade(mission);
  else openAnimatedMission(mission, format);
  if (content?.source === "ai") {
    modal.append(paragraph(content.narration, "source"));
  }
}

export function openChapterExplainer(mission) {
  const level = levels.find((item) => item.mission === mission) || levels[0];
  showModal("Learning Studio", level.title.toUpperCase());
  modal.append(
    paragraph("Watch the science unfold, then take control of the mission."),
  );
  const grid = document.createElement("div");
  grid.className = "experience-picker";
  [
    [
      "WATCH CHAPTER FILM",
      "45 seconds of animated science, captions and optional voice.",
      "animated",
    ],
    [
      "PLAY SIGNAL SPRINT",
      "Five timed rounds. Choose the right gate, score points and protect three lives.",
      "mini_game",
    ],
    [
      "START RESCUE MISSION",
      "Restore the colony with working physics and visible results.",
      "simulation",
    ],
  ].forEach(([title, description, format]) => {
    const card = button(
      title,
      () => chooseFormat(level.mission, format),
      "experience-choice",
    );
    const detail = document.createElement("small");
    detail.textContent = description;
    card.append(detail);
    grid.append(card);
  });
  modal.append(grid);
}

window.addEventListener("open-chapter-explainer", (event) =>
  openChapterExplainer(event.detail),
);
