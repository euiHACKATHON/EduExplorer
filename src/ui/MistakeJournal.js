import { state } from "../state/GameState.js";
import { levels } from "../config.js";
import { showModal, modal, paragraph, button } from "./DialogueUI.js";

export function renderJournalBadge() {
  const badge = document.querySelector("#mistake-count");
  if (!badge) return;
  const open = state.data.mistakes.filter((item) => !item.resolved).length;
  badge.textContent = open;
  badge.hidden = open === 0;
}

export function openMistakeJournal() {
  const mistakes = [...state.data.mistakes].sort(
    (a, b) =>
      Number(a.resolved) - Number(b.resolved) || b.lastTried - a.lastTried,
  );
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
  const unresolved = mistakes.filter((item) => !item.resolved).length;
  summary.className = "journal-summary";
  summary.innerHTML = `<strong>${unresolved}</strong><span>${unresolved === 1 ? "question needs" : "questions need"} another look</span><small>${mistakes.length - unresolved} mastered</small>`;
  modal.append(summary);

  const list = document.createElement("div");
  list.className = "mistake-list";
  mistakes.forEach((item) => {
    const level = levels.find(
      (candidate) => candidate.mission === item.mission,
    );
    const card = document.createElement("article");
    card.className = `mistake-card${item.resolved ? " resolved" : ""}`;
    const status = item.resolved ? "Mastered" : "Review needed";
    const meta = document.createElement("div");
    meta.className = "mistake-meta";
    const subject = document.createElement("span");
    subject.textContent = `${level?.constellation || ""} ${item.subject}`;
    const statusLabel = document.createElement("em");
    statusLabel.textContent = status;
    meta.append(subject, statusLabel);
    const question = document.createElement("h3");
    question.textContent = item.question;
    const answer = document.createElement("p");
    const answerLabel = document.createElement("small");
    answerLabel.textContent = "Your answer";
    answer.append(answerLabel, `${item.answerId}. ${item.answerText}`);
    const note = document.createElement("p");
    note.className = "mistake-note";
    note.textContent =
      item.feedback || "Review the lesson and try the question again.";
    card.append(meta, question, answer, note);
    if (item.attempts > 1) {
      const attempts = document.createElement("span");
      attempts.className = "attempt-count";
      attempts.textContent = `Tried ${item.attempts} times`;
      card.append(attempts);
    }
    const review = button(
      item.resolved ? "Practise again" : "Review question",
      () =>
        window.dispatchEvent(
          new CustomEvent("review-question", { detail: item.mission }),
        ),
      item.resolved ? "secondary compact" : "primary compact",
    );
    card.append(review);
    list.append(card);
  });
  modal.append(list);
}

window.addEventListener("mistakes-changed", renderJournalBadge);
window.addEventListener("open-journal", openMistakeJournal);
