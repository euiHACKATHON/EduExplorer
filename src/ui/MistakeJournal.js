import { state } from "../state/GameState.js";
import { levels } from "../config.js";
import { showModal, modal, paragraph, button } from "./DialogueUI.js";

export function renderJournalBadge() {
  // Kept as a harmless compatibility hook for callers after the visual
  // notification badge was removed from the Quest Log button.
}

export function openMistakeJournal() {
  // Mastered items stay in saved history but are intentionally absent from
  // the Quest Log: a correct practice retry clears the learner's to-do list.
  const byQuestion = new Map();
  state.data.mistakes
    .filter((item) => !item.resolved)
    .forEach((item) => {
      const saved = byQuestion.get(item.questionId);
      if (!saved || item.lastTried > saved.lastTried) byQuestion.set(item.questionId, item);
    });
  const mistakes = [...byQuestion.values()].sort((a, b) => b.lastTried - a.lastTried);
  showModal("Learning journal", "REVIEW & IMPROVE");
  modal.classList.add("journal-modal");
  modal.addEventListener(
    "close",
    () => modal.classList.remove("journal-modal"),
    { once: true },
  );

  if (!mistakes.length) {
    modal.append(
      paragraph(
        "No mistakes recorded yet. Questions you miss will appear here with your answer so you can practise them again.",
        "journal-empty",
      ),
    );
    return;
  }

  const summary = document.createElement("div");
  const unresolved = mistakes.length;
  summary.className = "journal-summary";
  summary.innerHTML = `<strong>${unresolved}</strong><span>${unresolved === 1 ? "question needs" : "questions need"} another look</span><small>Correct retries leave this log</small>`;
  modal.append(summary);

  const list = document.createElement("div");
  list.className = "mistake-list";
  mistakes.forEach((item) => {
    const level = levels.find(
      (candidate) => candidate.mission === item.mission,
    );
    const card = document.createElement("article");
    card.className = "mistake-card";
    const meta = document.createElement("div");
    meta.className = "mistake-meta";
    const subject = document.createElement("span");
    subject.textContent = `CHAPTER ${level ? levels.indexOf(level) + 1 : "?"} // ${level?.title.replace(/^Chapter \d+ · /, "") || item.subject}`;
    const statusLabel = document.createElement("em");
    statusLabel.textContent = "Review needed";
    meta.append(subject, statusLabel);
    const question = document.createElement("h3");
    question.textContent = item.question;
    const note = document.createElement("p");
    note.className = "mistake-note";
    note.textContent =
      item.feedback || "Review the lesson and try the question again.";
    card.append(meta, question, note);
    if (item.attempts > 1) {
      const attempts = document.createElement("span");
      attempts.className = "attempt-count";
      attempts.textContent = `Tried ${item.attempts} times`;
      card.append(attempts);
    }
    const review = button(
      "Practise question",
      () =>
        window.dispatchEvent(
          new CustomEvent("review-question", {
            detail: { mission: item.mission, questionId: item.questionId },
          }),
        ),
      "primary compact",
    );
    card.append(review);
    list.append(card);
  });
  modal.append(list);
}

window.addEventListener("mistakes-changed", renderJournalBadge);
window.addEventListener("open-journal", openMistakeJournal);
