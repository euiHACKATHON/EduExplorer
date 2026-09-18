import { api } from "../api/APIService.js";
import { state } from "../state/GameState.js";
import {
  showModal,
  modal,
  paragraph,
  button,
  closeModal,
  modalRevision,
  isCurrentModal,
} from "./DialogueUI.js";
import { renderProgress } from "./ProgressUI.js";
import { getLevel, levels } from "../config.js";

function showVictory(mission, result) {
  const levelIndex = getLevel(mission);
  const level = levels[levelIndex];
  const nextLevel = levels[levelIndex + 1];
  showModal(
    nextLevel ? `${level.title} restored` : "The zodiac is restored",
    nextLevel ? "LEVEL COMPLETE" : "FINAL VICTORY",
  );
  const victory = document.createElement("div");
  victory.className = "victory-card";
  victory.innerHTML = `
    <div class="victory-burst"><span>${level.constellation}</span></div>
    <p class="victory-label">REALM ${levelIndex + 1} CLEARED</p>
    <h3>${level.objective}</h3>
    <div class="victory-reward"><strong>+${result.xp_earned}</strong><small> STAR XP</small></div>
    <div class="victory-path" aria-label="Level completion path">
      ${levels
        .map(
          (item, index) =>
            `<span class="${index <= levelIndex ? "won" : index === levelIndex + 1 ? "unlocked" : ""}">${index <= levelIndex ? "✓" : item.constellation}</span>${index < levels.length - 1 ? "<i></i>" : ""}`,
        )
        .join("")}
    </div>`;
  modal.append(victory);

  if (nextLevel) {
    const unlock = document.createElement("div");
    unlock.className = "unlock-reveal";
    unlock.innerHTML = `<small>NEW REALM UNLOCKED</small><strong>${nextLevel.constellation} ${nextLevel.title}</strong><span>${nextLevel.subtitle}</span>`;
    modal.append(unlock);
    modal.append(
      button(`Travel to Realm ${levelIndex + 2} →`, () => {
        closeModal();
        window.dispatchEvent(
          new CustomEvent("enter-level", { detail: levelIndex + 1 }),
        );
      }),
    );
  } else {
    modal.append(
      paragraph(
        "Every guardian star is shining. You have mastered all three celestial trials.",
        "victory-message",
      ),
      button("Return to the realm →", closeModal),
    );
  }
}
export async function openChallenge(id, options = {}) {
  if (!state.isMissionUnlocked(id)) {
    showModal("Level locked", "TRAINING SEQUENCE");
    modal.append(
      paragraph("Pass the previous level's quiz before starting this one."),
    );
    return;
  }
  showModal("Preparing your mission…", "MISSION CONTROL");
  const loadToken = modalRevision();
  let q;
  try {
    q = await api.getChallenge(id);
  } catch (e) {
    if (isCurrentModal(loadToken)) modal.append(paragraph(e.message, "error"));
    return;
  }
  if (!isCurrentModal(loadToken)) return;
  showModal(q.title, `${q.subject.toUpperCase()} / ${q.mission_id}`);
  const token = modalRevision();
  modal.append(paragraph(q.context), paragraph(q.question, "question"));
  let selected = null,
    hints = 0,
    finished = false,
    busy = false;
  const started = performance.now();
  const choices = document.createElement("div");
  choices.className = "choices";
  choices.setAttribute("role", "group");
  choices.setAttribute("aria-label", "Answer choices");
  const feedback = paragraph("", "feedback");
  feedback.setAttribute("aria-live", "polite");
  const hintBox = paragraph("", "hint");
  hintBox.hidden = true;
  const updateControls = () => {
    choices
      .querySelectorAll("button")
      .forEach((b) => (b.disabled = busy || finished));
    submit.disabled = busy || finished || !selected;
    hintButton.disabled = busy || finished || hints >= 3;
  };
  const run = async (fn) => {
    if (busy || finished) return;
    busy = true;
    updateControls();
    try {
      await fn();
    } catch (e) {
      if (isCurrentModal(token)) {
        feedback.textContent = e.message;
        feedback.className = "feedback error";
      }
    } finally {
      busy = false;
      updateControls();
    }
  };
  q.options.forEach((o) => {
    const b = button(
      `${o.id}   ${o.text}`,
      () => {
        selected = o.id;
        choices.querySelectorAll("button").forEach((x) => {
          x.classList.remove("selected");
          x.setAttribute("aria-pressed", "false");
        });
        b.classList.add("selected");
        b.setAttribute("aria-pressed", "true");
        updateControls();
      },
      "choice",
    );
    b.setAttribute("aria-pressed", "false");
    choices.append(b);
  });
  const hintButton = button(
    "✦ Get a hint (0/3)",
    () =>
      run(async () => {
        const data = await api.requestHint({
          mission_id: id,
          question_id: q.question_id,
          student_id: state.data.student_id,
          level: hints + 1,
        });
        if (!isCurrentModal(token)) return;
        hints++;
        hintBox.hidden = false;
        hintBox.textContent = `${data.source === "ai" ? "AI tutor" : data.source === "authored-fallback" ? "AI unavailable · field guide" : "Field guide"} · ${data.hint}`;
        hintButton.textContent =
          hints === 3 ? "All 3 hints revealed" : `✦ Get a hint (${hints}/3)`;
      }),
    "secondary",
  );
  const submit = button("Check answer →", () =>
    run(async () => {
      const result = await api.submitAssessment({
        student_id: state.data.student_id,
        mission_id: id,
        question_id: q.question_id,
        answer: selected,
        time_taken: Math.min(
          86400,
          Math.round((performance.now() - started) / 1000),
        ),
        hints_used: hints,
      });
      // The server may accept a submission even if the learner closes its dialog.
      if (!isCurrentModal(token)) return;
      const wasCompleted = state.data.completed.includes(id);
      state.award(id, result);
      if (result.correct) state.resolveMistakes(q.question_id);
      else state.recordMistake(q, selected, result.feedback);
      renderProgress();
      window.dispatchEvent(new Event("mistakes-changed"));
      feedback.textContent = result.feedback;
      feedback.className = `feedback ${result.correct ? "success" : "error"}`;
      if (result.correct) {
        finished = true;
        window.dispatchEvent(
          new CustomEvent("mission-complete", { detail: id }),
        );
        if (options.review && wasCompleted) {
          showModal("Mistake mastered", "LEARNING JOURNAL");
          modal.append(
            paragraph(
              "You answered this question correctly. It is now marked as mastered in your journal.",
              "review-success",
            ),
            button("Back to the journal", () =>
              window.dispatchEvent(new Event("open-journal")),
            ),
          );
        } else showVictory(id, result);
      }
    }),
  );
  updateControls();
  modal.append(choices, hintBox, feedback, hintButton, submit);
}

window.addEventListener("review-question", (event) =>
  openChallenge(event.detail, { review: true }),
);
