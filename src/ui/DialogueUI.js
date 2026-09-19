import { api } from "../api/APIService.js";
import { openChallenge } from "./ChallengeUI.js";
import { state } from "../state/GameState.js";
import { getLevel } from "../config.js";
export const modal = document.querySelector("#overlay");
let opener;
let revision = 0;
modal.addEventListener("close", () => {
  revision++;
  opener?.focus?.();
});
export const modalRevision = () => revision;
export const isCurrentModal = (token) => modal.open && token === revision;
export function closeModal() {
  modal.close();
}
export function showModal(title, eyebrow = "COLONY COMMS") {
  revision++;
  if (!modal.open) opener = document.activeElement;
  modal.replaceChildren();
  const top = document.createElement("div");
  top.className = "modal-top";
  const label = paragraph(eyebrow, "eyebrow");
  const close = button("×", closeModal, "close");
  close.setAttribute("aria-label", "Close dialog");
  top.append(label, close);
  const h = document.createElement("h2");
  h.id = "modal-title";
  h.textContent = title;
  modal.append(top, h);
  if (!modal.open) modal.showModal();
  return modal;
}
export function paragraph(text, className = "") {
  const p = document.createElement("p");
  p.className = className;
  p.textContent = text;
  return p;
}
export function button(text, action, className = "primary") {
  const b = document.createElement("button");
  b.className = className;
  b.textContent = text;
  b.onclick = action;
  return b;
}
// Labeled text input for simple in-modal forms (e.g. sign-in/sign-up).
// Returns the wrapping <label>; read/write the value via `wrap.input.value`.
export function field(labelText, opts = {}) {
  const wrap = document.createElement("label");
  wrap.className = "field";
  const span = document.createElement("span");
  span.textContent = labelText;
  const input = document.createElement("input");
  input.type = opts.type || "text";
  if (opts.placeholder) input.placeholder = opts.placeholder;
  if (opts.autocomplete) input.autocomplete = opts.autocomplete;
  if (opts.maxLength) input.maxLength = opts.maxLength;
  wrap.append(span, input);
  wrap.input = input;
  return wrap;
}
export async function pending(b, fn) {
  b.disabled = true;
  try {
    await fn();
  } catch (e) {
    if (b.isConnected && modal.open) {
      const p = paragraph(e.message, "error");
      p.setAttribute("role", "alert");
      modal.append(p);
    }
  } finally {
    b.disabled = false;
  }
}
export async function dialogue(npc) {
  if (!state.isMissionUnlocked(npc.mission)) {
    const level = getLevel(npc.mission) + 1;
    showModal(`Level ${level} is locked`, "TRAINING SEQUENCE");
    modal.append(
      paragraph(`Pass Level ${level - 1}'s quiz to unlock this lesson.`),
    );
    return;
  }
  showModal(npc.name, npc.role.toUpperCase());
  const token = modalRevision();
  const loading = paragraph("Connecting to your crewmate…");
  modal.append(loading);
  try {
    const data = await api.getNPCDialogue(npc.id);
    if (!isCurrentModal(token)) return;
    loading.textContent = data.message;
    modal.append(
      paragraph(
        data.source === "ai"
          ? "AI GENERATED DIALOGUE"
          : data.source === "authored-fallback"
            ? "◇ AI unavailable · authored backup dialogue"
            : "◇ Authored expedition dialogue",
        "source",
      ),
    );
    for (const option of data.options) {
      const b = button(
        option.text,
        () =>
          pending(b, async () => {
            if (option.action === "START_CHALLENGE")
              await openChallenge(option.payload);
            else {
              const info = await api.explain(npc.mission);
              if (!isCurrentModal(token)) return;
              modal.append(
                paragraph(info.message, "hint"),
                paragraph(
                  info.source === "ai"
                    ? "AI GENERATED EXPLANATION"
                    : "◇ Authored explanation",
                  "source",
                ),
              );
            }
          }),
        option.action === "START_CHALLENGE" ? "primary" : "secondary",
      );
      modal.append(b);
    }
    if (!api.useMock) {
      modal.append(
        button(
          "ASK AI ABOUT THIS LESSON",
          () => {
            closeModal();
            window.dispatchEvent(
              new CustomEvent("open-ai-tutor", { detail: npc.mission }),
            );
          },
          "secondary ask-ai-dialogue",
        ),
      );
    }
  } catch (e) {
    if (isCurrentModal(token)) {
      loading.textContent = e.message;
      loading.className = "error";
    }
  }
}