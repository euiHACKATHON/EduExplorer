import {
  button,
  modal,
  paragraph,
  showModal,
  modalRevision,
  isCurrentModal,
} from "./DialogueUI.js";

// Self-contained arcade rounds: no chapter XP or rescue progression is changed.
export function openScienceArcade(mission) {
  showModal("Signal sprint", "SCIENCE ARCADE • FIVE ROUNDS");
  const token = modalRevision();
  const prompt = paragraph("", "hint");
  const canvas = document.createElement("canvas");
  canvas.width = 900;
  canvas.height = 320;
  canvas.style.cssText =
    "width:100%;background:#080f25;border-radius:12px;display:block";
  canvas.setAttribute(
    "aria-label",
    "Animated signal gates; select your answer using the buttons below.",
  );
  const choices = document.createElement("div");
  choices.className = "simulation-choices";
  const feedback = paragraph(
    "Choose the correct gate before the signal arrives. Wrong answers cost a life.",
    "feedback",
  );
  feedback.setAttribute("aria-live", "polite");
  const hud = paragraph("", "experience-goal");
  const actions = document.createElement("div");
  actions.className = "simulation-choices";
  modal.append(hud, prompt, canvas, choices, feedback, actions);
  let round = 0,
    score = 0,
    lives = 3,
    remaining = 15,
    last = performance.now(),
    playing = false,
    finished = false,
    answer = 0,
    values = [],
    resolved = false;
  const next = button("Start sprint", () => {
    if (finished) {
      round = 0;
      score = 0;
      lives = 3;
      finished = false;
    }
    begin();
  });
  actions.append(next);
  const pause = button(
    "Pause",
    () => {
      if (resolved || finished || round === 0) return;
      playing = !playing;
      pause.textContent = playing ? "Pause" : "Resume";
      for (const b of choices.children) b.disabled = !playing;
    },
    "secondary",
  );
  actions.append(pause);
  actions.append(
    button(
      "Chapter questions →",
      () =>
        window.dispatchEvent(
          new CustomEvent("open-chapter-quiz", { detail: mission }),
        ),
      "secondary",
    ),
  );
  function begin() {
    round++;
    remaining = 15;
    resolved = false;
    playing = true;
    next.hidden = true;
    pause.textContent = "Pause";
    const n = 2 + Math.floor(Math.random() * 5);
    let unit;
    if (mission === "M001") {
      const mass = 100 * n;
      const acceleration = 2 + (round % 3);
      answer = mass * acceleration;
      unit = "N";
      prompt.textContent = `Route the rover: ${mass} kg needs ${acceleration} m/s². Which net force?`;
    } else if (mission === "M002") {
      answer = 10 + n * 7;
      unit = "°";
      prompt.textContent = `A ray arrives at ${answer}° from the normal. Which reflected angle opens the gate?`;
    } else {
      const power = 100 * n;
      const hours = 1 + round;
      answer = power * hours;
      unit = "Wh";
      prompt.textContent = `Power sprint: ${power} W for ${hours} hours. How much energy is transferred?`;
    }
    const offset = mission === "M002" ? 10 : 100;
    values = [answer, answer + offset, answer + offset * 2].sort(
      () => Math.random() - 0.5,
    );
    choices.replaceChildren();
    values.forEach((v, i) =>
      choices.append(
        button(`Gate ${i + 1}: ${v} ${unit}`, () => resolve(v === answer)),
      ),
    );
    feedback.textContent =
      "Select a gate. Faster correct answers earn more points.";
  }
  function resolve(correct) {
    if (!playing || resolved) return;
    playing = false;
    resolved = true;
    for (const b of choices.children) b.disabled = true;
    if (correct) {
      const gain = 100 + Math.ceil(remaining) * 5;
      score += gain;
      feedback.textContent = `Gate opened! +${gain} points.`;
    } else {
      lives--;
      feedback.textContent = `Signal missed. The correct value was ${answer}.`;
    }
    finished = lives === 0 || round === 5;
    next.hidden = false;
    next.textContent = finished ? "Play again" : "Next round →";
    if (finished) feedback.textContent += ` Sprint finished: ${score} points.`;
  }
  const g = canvas.getContext("2d");
  function frame(now) {
    if (!isCurrentModal(token)) return;
    const dt = Math.min((now - last) / 1000, 0.1);
    last = now;
    if (playing) {
      remaining = Math.max(0, remaining - dt);
      if (remaining === 0) resolve(false);
    }
    hud.textContent = `ROUND ${round}/5  •  SCORE ${score}  •  LIVES ${lives}  •  ${Math.ceil(remaining)}s`;
    g.fillStyle = "#091326";
    g.fillRect(0, 0, 900, 320);
    for (let i = 0; i < 50; i++) {
      g.fillStyle = "#54708d";
      g.fillRect((i * 137) % 900, (i * 61) % 320, 2, 2);
    }
    for (let i = 0; i < 3; i++) {
      const y = 70 + i * 90;
      g.strokeStyle = "#29445c";
      g.lineWidth = 2;
      g.beginPath();
      g.moveTo(30, y);
      g.lineTo(840, y);
      g.stroke();
      g.strokeStyle = resolved && values[i] === answer ? "#8bffc8" : "#7acfe6";
      g.lineWidth = 5;
      g.strokeRect(745, y - 30, 120, 60);
      g.fillStyle = "#ecf5ff";
      g.font = "20px sans-serif";
      g.fillText(String(values[i] ?? "?"), 775, y + 7);
      const x = 50 + (1 - remaining / 15) * 650;
      g.fillStyle = "#ffcd7c";
      g.beginPath();
      g.arc(x, y, 9, 0, Math.PI * 2);
      g.fill();
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
