import {
  button,
  modal,
  paragraph,
  showModal,
  modalRevision,
  isCurrentModal,
} from "./DialogueUI.js";

const chapters = {
  M001: {
    title: "Rescue on the crimson dunes",
    unit: "Net force (N)",
    max: 3000,
    step: 100,
    rounds: [
      [500, 2],
      [500, 4],
      [1000, 2],
    ],
    script: [
      "The rover is carrying supplies across Mars. Net force changes its velocity; mass resists that change.",
      "With 500 kg of cargo and 1,000 N of net force, acceleration is 2 m/s². Watch its speed increase.",
      "Double the net force to 2,000 N. With the same mass, acceleration doubles to 4 m/s².",
      "Now double the mass to 1,000 kg. The same 2,000 N produces only 2 m/s². Force, mass and acceleration obey F = ma.",
    ],
  },
  M002: {
    title: "The lost light signal",
    unit: "Incident angle from normal (°)",
    max: 70,
    step: 1,
    rounds: [
      [25, 25],
      [45, 45],
      [60, 60],
    ],
    script: [
      "A communications beam must bounce off a mirror to reach a receiver. The dashed line is the normal, perpendicular to the mirror.",
      "Light arrives at 25 degrees from the normal. It reflects at 25 degrees on the other side.",
      "Aim at 45 degrees. The outgoing beam also moves to 45 degrees. Both angles are measured from the normal, not the mirror.",
      "The receiver moves again. To reach it, match its direction: angle of incidence equals angle of reflection.",
    ],
  },
  M003: {
    title: "Restore the night outpost",
    unit: "Operating time (hours)",
    max: 10,
    step: 1,
    rounds: [
      [200, 600],
      [200, 1000],
      [400, 1200],
    ],
    script: [
      "Night has reached the colony. A generator transfers energy into a battery. Power measures how quickly that transfer happens.",
      "At 200 watts, three hours transfers 600 watt-hours. Watch the battery fill as the clock advances.",
      "Run the same generator for five hours: 200 times 5 gives 1,000 watt-hours, or one kilowatt-hour.",
      "At 400 watts, three hours transfers 1,200 watt-hours. More power transfers more energy in the same time: E = Pt.",
    ],
  },
};

const rescue = {
  M001: [
    "Free the supply rover",
    "Cross the exposed valley",
    "Deliver the heavy medicine cargo",
  ],
  M002: [
    "Reconnect the landing beacon",
    "Restore the relay tower",
    "Contact the rescue ship",
  ],
  M003: [
    "Power the emergency lights",
    "Restart the oxygen station",
    "Restore the habitat",
  ],
};

export function openAnimatedMission(mission, format) {
  const cfg = chapters[mission];
  if (!cfg) return;
  const film = format === "animated";
  showModal(
    cfg.title,
    film ? "45 SECOND CHAPTER FILM" : "COLONY RESCUE • THREE MISSIONS",
  );
  const token = modalRevision();
  const canvas = document.createElement("canvas");
  canvas.width = 900;
  canvas.height = 420;
  canvas.style.cssText =
    "width:100%;display:block;border-radius:12px;background:#080f25;margin:12px 0";
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label", cfg.title);
  const caption = paragraph("", "hint");
  caption.setAttribute("aria-live", "polite");
  const status = paragraph("", "feedback");
  status.setAttribute("aria-live", "polite");
  const controls = document.createElement("div");
  controls.className = "simulation-choices";
  modal.append(canvas, caption, controls, status);
  const route = paragraph("", "experience-goal");
  if (!film) modal.insertBefore(route, canvas);
  const g = canvas.getContext("2d");
  let round = 0,
    elapsed = 0,
    last = performance.now(),
    playing = false,
    running = false,
    trial = 0,
    success = false,
    done = false,
    value = 0,
    spoken = -1;
  let voice = false;
  let inspected = false;
  const inspect = button(
    "Scan the equipment",
    () => {
      inspected = true;
      slider.disabled = false;
      action.disabled = false;
      inspect.disabled = true;
      status.textContent =
        "Scan complete. Set the control using the measurements in your objective.";
    },
    "secondary",
  );
  const text = (s, x, y, size = 18, color = "#dcefff") => {
    g.fillStyle = color;
    g.font = `${size}px sans-serif`;
    g.fillText(s, x, y);
  };
  const line = (x, y, xx, yy, color, width = 3) => {
    g.strokeStyle = color;
    g.lineWidth = width;
    g.beginPath();
    g.moveTo(x, y);
    g.lineTo(xx, yy);
    g.stroke();
  };
  const circle = (x, y, r, color) => {
    g.fillStyle = color;
    g.beginPath();
    g.arc(x, y, r, 0, Math.PI * 2);
    g.fill();
  };
  const slider = document.createElement("input");
  slider.type = "range";
  slider.min = "0";
  slider.max = cfg.max;
  slider.step = cfg.step;
  slider.value = "0";
  slider.setAttribute("aria-label", cfg.unit);
  const readout = paragraph("");
  slider.oninput = () => {
    value = Number(slider.value);
    readout.textContent = `${cfg.unit}: ${value}`;
  };
  slider.oninput();
  for (const name of ["keydown", "keyup"])
    slider.addEventListener(name, (e) => e.stopPropagation());
  function target() {
    const [a, b] = cfg.rounds[round];
    return mission === "M001" ? a * b : mission === "M002" ? a : b / a;
  }
  function brief() {
    const [a, b] = cfg.rounds[round];
    caption.textContent = film
      ? cfg.script[Math.min(3, Math.floor(elapsed / 11.25))]
      : `Mission ${round + 1}/3 — ` +
        (mission === "M001"
          ? `Move the ${a} kg rover with an acceleration of ${b} m/s². Set the net force, then launch.`
          : mission === "M002"
            ? `The receiver is ${a}° from the normal. Aim the incoming beam to reach it.`
            : `Transfer exactly ${b} Wh using a ${a} W generator. Choose its operating time.`);
    if (!film)
      route.textContent = rescue[mission]
        .map(
          (name, i) =>
            `${i < round || (i === round && success) ? "✓" : i === round ? "▶" : "○"} ${name}`,
        )
        .join("  →  ");
  }
  const action = button("Launch mission", () => {
    if (done) return;
    if (success) {
      round++;
      success = false;
      inspected = false;
      inspect.disabled = false;
      value = 0;
      slider.value = "0";
      slider.oninput();
      status.textContent =
        "New sector reached. Scan the equipment to reveal its controls.";
      brief();
      action.textContent = "Launch mission";
      slider.disabled = true;
      action.disabled = true;
      return;
    }
    if (!inspected) return;
    running = true;
    trial = 0;
    action.disabled = true;
    slider.disabled = true;
    status.textContent = "Mission running…";
  });
  if (film) {
    const play = button("Play / pause", () => {
      if (elapsed >= 45) {
        elapsed = 0;
        spoken = -1;
      }
      playing = !playing;
      if (!playing) window.speechSynthesis?.cancel();
    });
    const narration = button(
      "Voice: off",
      () => {
        voice = !voice;
        narration.textContent = voice ? "Voice: on" : "Voice: off";
        spoken = -1;
        if (!voice) window.speechSynthesis?.cancel();
      },
      "secondary",
    );
    controls.append(
      play,
      narration,
      button(
        "Replay",
        () => {
          elapsed = 0;
          spoken = -1;
          playing = true;
        },
        "secondary",
      ),
    );
  } else {
    controls.append(inspect, slider, readout, action);
    slider.disabled = true;
    action.disabled = true;
  }
  controls.append(
    button(
      "Chapter questions →",
      () =>
        window.dispatchEvent(
          new CustomEvent("open-chapter-quiz", { detail: mission }),
        ),
      "secondary",
    ),
  );
  brief();
  function frame(now) {
    if (!isCurrentModal(token)) {
      if (voice) window.speechSynthesis?.cancel();
      return;
    }
    const dt = Math.min((now - last) / 1000, 0.05);
    last = now;
    if (film && playing) {
      elapsed = Math.min(45, elapsed + dt);
      if (elapsed === 45) playing = false;
    }
    if (running) trial += dt;
    const beat = Math.min(3, Math.floor(elapsed / 11.25));
    if (film) {
      round = Math.max(0, beat - 1);
      value = target();
      brief();
      if (playing && voice && spoken !== beat && "speechSynthesis" in window) {
        spoken = beat;
        window.speechSynthesis.cancel();
        window.speechSynthesis.speak(
          new SpeechSynthesisUtterance(cfg.script[beat]),
        );
      }
    }
    g.clearRect(0, 0, 900, 420);
    const sky = g.createLinearGradient(0, 0, 0, 420);
    sky.addColorStop(0, "#071023");
    sky.addColorStop(1, mission === "M001" ? "#613549" : "#163d53");
    g.fillStyle = sky;
    g.fillRect(0, 0, 900, 420);
    for (let i = 0; i < 65; i++)
      circle((i * 137) % 900, (i * 59) % 270, 1 + (i % 2), "#adcee8");
    circle(780, 65, 32, "#48627c");
    g.fillStyle = "#202d43";
    g.beginPath();
    g.moveTo(0, 325);
    for (let x = 0; x <= 900; x += 40)
      g.lineTo(x, 295 + Math.sin(x * 0.016) * 24);
    g.lineTo(900, 420);
    g.lineTo(0, 420);
    g.fill();
    const t = film
      ? (elapsed % 11.25) / 11.25
      : running
        ? Math.min(trial / 4, 1)
        : success
          ? 1
          : 0;
    const [a, b] = cfg.rounds[round];
    if (!film) {
      for (let i = 0; i < 3; i++) {
        const restored = i < round || (i === round && success);
        g.fillStyle = restored ? "#8bf0b7" : "#46556b";
        g.fillRect(30 + i * 75, 110, 55, 35);
        text(
          restored ? "ONLINE" : "OFFLINE",
          32 + i * 75,
          136,
          10,
          restored ? "#102b25" : "#fff",
        );
      }
      text(rescue[mission][round], 330, 125, 18, "#ffdc9e");
    }
    if (mission === "M001") {
      const acceleration = value / a;
      const simSeconds = t * 4;
      const x =
        90 + Math.min(660, 0.5 * acceleration * simSeconds * simSeconds * 10);
      g.fillStyle = "#566c7a";
      g.fillRect(770, 235, 90, 120);
      text("BASE", 785, 230, 18);
      g.fillStyle = "#e9bc73";
      g.fillRect(x, 285, 90, 40);
      g.fillStyle = "#75e7ef";
      g.fillRect(x + 20, 263, 40, 25);
      for (const offset of [15, 75]) {
        circle(x + offset, 330, 15, "#0b1523");
        line(
          x + offset,
          330,
          x + offset + Math.cos(simSeconds * acceleration) * 11,
          330 + Math.sin(simSeconds * acceleration) * 11,
          "#88a8b7",
        );
      }
      if (t > 0) {
        line(x + 95, 305, x + 135 + value / 45, 305, "#7fe7ff", 5);
        text("F", x + 102, 290);
        for (let j = 0; j < 8; j++)
          circle(
            x - ((t * 100 + j * 17) % 90),
            334 + (j % 3) * 3,
            2,
            "#c28d77",
          );
      }
      text(`Mass ${a} kg    Net force ${value} N`, 30, 40, 22);
      text(
        `a = F ÷ m = ${acceleration.toFixed(1)} m/s²`,
        30,
        75,
        22,
        "#8bf0da",
      );
      text(
        `Time ${simSeconds.toFixed(1)} s    Speed ${(acceleration * simSeconds).toFixed(1)} m/s`,
        30,
        395,
      );
    } else if (mission === "M002") {
      const cx = 450,
        cy = 310,
        r = 220,
        ang = (value * Math.PI) / 180,
        goal = (a * Math.PI) / 180;
      line(270, cy + 5, 630, cy + 5, "#c0e9fa", 9);
      g.setLineDash([8, 7]);
      line(cx, cy, cx, 80, "#a4b6c9", 2);
      g.setLineDash([]);
      text("NORMAL", cx + 8, 100, 14);
      const sx = cx - Math.sin(ang) * r,
        sy = cy - Math.cos(ang) * r,
        ex = cx + Math.sin(ang) * r,
        ey = sy;
      line(sx, sy, cx, cy, "#ffcf78", 4);
      line(cx, cy, ex, ey, "#81f4dd", 4);
      const p = ((film ? elapsed : trial) % 2) / 2;
      circle(sx + (cx - sx) * p, sy + (cy - sy) * p, 6, "#fff6c5");
      circle(cx + (ex - cx) * p, cy + (ey - cy) * p, 6, "#caffed");
      const rx = cx + Math.sin(goal) * r,
        ry = cy - Math.cos(goal) * r;
      circle(rx, ry, 18, success ? "#8bf0b7" : "#617587");
      circle(rx, ry, 9, "#122637");
      text("RECEIVER", rx - 35, ry - 25, 13);
      text(`${value}°`, cx - 65, cy - 75);
      text(`${value}°`, cx + 25, cy - 75);
      text("Incident angle = reflected angle", 30, 40, 24);
      text("Angles are measured from the dashed normal.", 30, 395, 18);
    } else {
      const energy = a * value * t,
        fill = Math.min(1, energy / b);
      g.fillStyle = "#344b64";
      g.fillRect(70, 190, 140, 145);
      text("GENERATOR", 78, 177, 16);
      circle(140, 255, 40, "#163c50");
      for (let i = 0; i < 3; i++) {
        const angle = t * 25 + (i * Math.PI * 2) / 3;
        line(
          140,
          255,
          140 + Math.cos(angle) * 34,
          255 + Math.sin(angle) * 34,
          "#79e4d3",
          7,
        );
      }
      line(210, 270, 470, 270, "#5b879d", 6);
      for (let j = 0; j < 8; j++)
        circle(220 + ((j * 30 + t * 250) % 240), 270, 4, "#80f6c5");
      g.fillStyle = "#172a40";
      g.fillRect(480, 170, 130, 165);
      g.fillStyle = energy > b ? "#ffa67b" : "#7aefc9";
      g.fillRect(490, 325 - fill * 145, 110, fill * 145);
      g.strokeStyle = "#c8e6ec";
      g.lineWidth = 3;
      g.strokeRect(480, 170, 130, 165);
      text("BATTERY", 498, 150);
      for (let i = 0; i < 4; i++) {
        g.fillStyle = "#344b64";
        g.fillRect(650 + i * 55, 230, 45, 105);
        g.fillStyle = fill > i / 4 ? "#ffe29b" : "#15243b";
        g.fillRect(660 + i * 55, 248, 25, 25);
      }
      text(
        `${a} W × ${(value * t).toFixed(1)} h = ${energy.toFixed(0)} Wh`,
        30,
        40,
        24,
      );
      text(`Target: ${b} Wh`, 30, 75, 22, "#8bf0da");
      text("Energy stored lights the colony.", 30, 395);
    }
    if (film) {
      g.fillStyle = "#7fe7ff";
      g.fillRect(0, 414, (900 * elapsed) / 45, 6);
      text(`${Math.floor(elapsed)} / 45 seconds`, 680, 395, 16);
    }
    if (running && trial >= 4) {
      running = false;
      success = value === target();
      action.disabled = false;
      brief();
      status.textContent = success
        ? "Objective achieved. Supplies secured!"
        : `Try again. ` +
          (mission === "M001"
            ? "Use net force = mass × required acceleration."
            : mission === "M002"
              ? "The beam reflects at the same angle you set for incidence."
              : "Multiply watts by hours and compare with the energy target.");
      if (success && round === 2) {
        done = true;
        action.disabled = true;
        action.textContent = "All missions complete";
        status.textContent = "Colony restored — all three objectives achieved!";
      } else {
        action.textContent = success ? "Next mission →" : "Retry mission";
        slider.disabled = success;
      }
    }
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
}
