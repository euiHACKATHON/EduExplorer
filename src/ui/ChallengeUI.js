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
export async function openChallenge(id) {
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
      state.award(id, result);
      renderProgress();
      feedback.textContent = result.feedback;
      feedback.className = `feedback ${result.correct ? "success" : "error"}`;
      if (result.correct) {
        finished = true;
        submit.hidden = true;
        hintButton.hidden = true;
        modal.append(
          paragraph(
            `+${result.xp_earned} XP · Colony system restored`,
            "reward",
          ),
          button("Return to the colony →", closeModal),
        );
        window.dispatchEvent(
          new CustomEvent("mission-complete", { detail: id }),
        );
      }
    }),
  );
  updateControls();
  modal.append(choices, hintBox, feedback, hintButton, submit);
}
