import { api } from "../api/APIService.js";
import { levels } from "../config.js";
import { button, modal, paragraph, showModal } from "./DialogueUI.js";
import { sigilHTML } from "./PixelSigil.js";

let activeLevel = 0;
const histories = new Map();

window.addEventListener("realm-changed", (event) => {
  activeLevel = event.detail;
});

function addMessage(log, role, text, source = "") {
  const row = document.createElement("div");
  row.className = `tutor-message ${role}`;
  const label = document.createElement("small");
  label.textContent = role === "student" ? "YOU" : "TUTOR UNIT";
  const body = document.createElement("p");
  body.textContent = text;
  row.append(label, body);
  if (source === "authored-fallback") {
    const status = document.createElement("em");
    status.textContent = "BACKUP FIELD NOTE";
    row.append(status);
  }
  log.append(row);
  log.scrollTop = log.scrollHeight;
}

export function setAITutorAvailable(available) {
  const trigger = document.querySelector("#ask-ai-button");
  if (trigger) trigger.hidden = !available;
}

export function openAITutor(missionId) {
  const requestedLevel = missionId
    ? levels.findIndex((level) => level.mission === missionId)
    : activeLevel;
  const level = levels[requestedLevel >= 0 ? requestedLevel : activeLevel] || levels[0];
  showModal(level.title, `AI TUTOR // ${level.subject.toUpperCase()}`);
  modal.classList.add("tutor-chat-modal");
  modal.addEventListener(
    "close",
    () => modal.classList.remove("tutor-chat-modal"),
    { once: true },
  );

  const lesson = document.createElement("div");
  lesson.className = "tutor-lesson-chip";
  lesson.innerHTML = `${sigilHTML(level)}<span><small>CURRENT LESSON</small><strong>${level.objective}</strong></span>`;
  const log = document.createElement("div");
  log.className = "tutor-log";
  log.setAttribute("aria-live", "polite");
  log.setAttribute("aria-label", "AI tutor conversation");

  const history = histories.get(level.mission) || [];
  if (!history.length)
    addMessage(
      log,
      "tutor",
      `Tutor link ready. Ask me anything about ${level.subject.toLowerCase()} in this mission. I will explain the method without giving away the quiz answer.`,
    );
  history.forEach((entry) => addMessage(log, entry.role, entry.text, entry.source));

  const form = document.createElement("form");
  form.className = "tutor-form";
  const input = document.createElement("input");
  input.type = "text";
  input.name = "question";
  input.maxLength = 500;
  input.autocomplete = "off";
  input.placeholder = "Ask about this lesson...";
  input.setAttribute("aria-label", "Question for the AI tutor");
  const send = button("SEND", null, "primary tutor-send");
  send.type = "submit";
  form.append(input, send);
  const error = paragraph("", "error tutor-error");

  form.onsubmit = async (event) => {
    event.preventDefault();
    const question = input.value.trim();
    if (question.length < 2 || send.disabled) return;
    error.textContent = "";
    input.value = "";
    addMessage(log, "student", question);
    history.push({ role: "student", text: question });
    histories.set(level.mission, history.slice(-12));
    input.disabled = true;
    send.disabled = true;
    send.textContent = "THINKING...";
    try {
      const response = await api.askTutor(level.mission, question);
      addMessage(log, "tutor", response.message, response.source);
      history.push({
        role: "tutor",
        text: response.message,
        source: response.source,
      });
      histories.set(level.mission, history.slice(-12));
    } catch (requestError) {
      error.textContent = requestError.message;
    } finally {
      input.disabled = false;
      send.disabled = false;
      send.textContent = "SEND";
      input.focus();
    }
  };

  modal.append(lesson, log, form, error);
  input.focus();
}

window.addEventListener("open-ai-tutor", (event) => openAITutor(event.detail));
