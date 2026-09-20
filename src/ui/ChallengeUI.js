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
import { sigilHTML } from "./PixelSigil.js";
import { chapterQuizzes } from "../data/chapterQuizzes.js";

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
    <div class="victory-burst">${sigilHTML(level, "pixel-sigil victory-sigil")}</div>
    <p class="victory-label">REALM ${levelIndex + 1} CLEARED</p>
    <h3>${level.objective}</h3>
    <div class="victory-reward"><strong>+${result.xp_earned}</strong><small> STAR XP</small></div>
    <div class="victory-path" aria-label="Level completion path">
      ${levels
        .map(
          (item, index) =>
            `<span class="${index <= levelIndex ? "won" : index === levelIndex + 1 ? "unlocked" : ""}">${index <= levelIndex ? "OK" : sigilHTML(item, "pixel-sigil path-sigil")}</span>${index < levels.length - 1 ? "<i></i>" : ""}`,
        )
        .join("")}
    </div>`;
  modal.append(victory);

  if (nextLevel) {
    const unlock = document.createElement("div");
    unlock.className = "unlock-reveal";
    unlock.innerHTML = `${sigilHTML(nextLevel, "pixel-sigil unlock-sigil")}<small>NEW WORLD UNLOCKED</small><strong>${nextLevel.title}</strong><span>${nextLevel.subtitle}</span>`;
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
    const questions = chapterQuizzes[id];
    if (!questions) throw new Error("This chapter has no assessment yet.");
    const completed = new Set(state.data.chapterProgress?.[id] || []);
    const next = options.questionId
      ? questions.find((item) => item.id === options.questionId)
      : questions.find((item) => !completed.has(item.id));
    if (!next) {
      showVictory(id, { xp_earned: 0 });
      return;
    }
    q = {
      ...next,
      question_id: next.id,
      mission_id: id,
      title: levels[getLevel(id)].title,
      subject: "Grade 9 Physics",
      context: `Question ${completed.size + 1} of 10`,
      options: next.options.map((text, index) => ({ id: "ABCD"[index], text })),
      hints: ["Read each science term carefully.", "Eliminate choices that use the wrong unit or definition.", "Use the chapter notes and try again."],
    };
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
    "HINT (0/3)",
    () =>
      run(async () => {
        const data = { hint: q.hints[Math.min(hints, q.hints.length - 1)], source: "offline" };
        if (!isCurrentModal(token)) return;
        hints++;
        hintBox.hidden = false;
        hintBox.textContent = `${data.source === "ai" ? "AI tutor" : data.source === "authored-fallback" ? "AI unavailable · field guide" : "Field guide"} · ${data.hint}`;
        hintButton.textContent =
          hints === 3 ? "ALL HINTS USED" : `HINT (${hints}/3)`;
      }),
    "secondary",
  );
  const submit = button("Check answer →", () =>
    run(async () => {
      const correct = selected === q.answer;
      const result = {
        correct,
        xp_earned: 0,
        mastery: 0,
        feedback: correct ? q.explanation : "Not quite. Review the chapter idea, use a hint if needed, and try again.",
      };
      // The server may accept a submission even if the learner closes its dialog.
      if (!isCurrentModal(token)) return;
      const chapter = state.answerChapterQuestion(id, q.question_id, correct, hints);
      // A normal retry helps the learner progress through the chapter, but it
      // should not silently erase a missed question from the Quest Log. Only
      // a deliberate practice retry launched from that log clears the item.
      if (result.correct && options.review) state.resolveMistakes(q.question_id);
      else if (!result.correct) state.recordMistake(q, selected, result.feedback);
      renderProgress();
      window.dispatchEvent(new Event("mistakes-changed"));
      feedback.textContent = result.feedback;
      feedback.className = `feedback ${result.correct ? "success" : "error"}`;
      if (result.correct) {
        finished = true;
        if (!chapter.complete) {
          showModal("Question mastered", "CHAPTER PROGRESS");
          modal.append(
            paragraph(`${chapter.answered} of 10 questions complete. Continue to the next question.`),
            button("Next question →", () => openChallenge(id)),
          );
        } else if (chapter.wasComplete) {
          showModal(
            options.review ? "Mistake mastered" : "Already mastered",
            "LEARNING JOURNAL",
          );
          modal.append(
            paragraph(
              options.review
                ? "You answered this question correctly. It is now marked as mastered in your journal."
                : "You've already earned XP for this quest, so no new Star XP this time — but nice review!",
              "review-success",
            ),
            button(
              options.review ? "Back to the journal" : "Continue",
              () =>
                options.review
                  ? window.dispatchEvent(new Event("open-journal"))
                  : closeModal(),
            ),
          );
        } else showVictory(id, { ...result, xp_earned: Math.max(250, 500 - hints * 15) });
      }
    }),
  );
  updateControls();
  modal.append(choices, hintBox, feedback, hintButton, submit);
}

window.addEventListener("review-question", (event) =>
  openChallenge(event.detail.mission, { review: true, questionId: event.detail.questionId }),
);
