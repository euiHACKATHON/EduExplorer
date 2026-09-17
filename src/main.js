import Phaser from "phaser";
import "./style.css";
import { WIDTH, HEIGHT } from "./config.js";
import { BootScene } from "./scenes/BootScene.js";
import { MainMenuScene } from "./scenes/MainMenuScene.js";
import { CharacterSelectScene } from "./scenes/CharacterSelectScene.js";
import { MarsColonyScene } from "./scenes/MarsColonyScene.js";
import { renderProgress } from "./ui/ProgressUI.js";
import { api } from "./api/APIService.js";
import { state } from "./state/GameState.js";
import {
  showModal,
  modal,
  paragraph,
  button,
  pending,
  closeModal,
} from "./ui/DialogueUI.js";
new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  width: WIDTH,
  height: HEIGHT,
  backgroundColor: "#b87451",
  physics: { default: "arcade", arcade: { debug: false } },
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [BootScene, MainMenuScene, CharacterSelectScene, MarsColonyScene],
});
renderProgress();
document.querySelector("#settings-button").onclick = () => {
  showModal("Expedition settings", "CONNECTION");
  modal.append(
    paragraph(
      "Offline mode is ready to play. Live AI uses the FastAPI service and its server-side OpenAI key.",
    ),
  );
  const offline = button(
    "Use offline lessons",
    () => {
      api.useMock = true;
      state.setMode("offline");
      renderProgress();
      document.querySelector("#mode-badge").textContent =
        "● OFFLINE EXPEDITION";
      closeModal();
    },
    "secondary",
  );
  const live = button("Connect to live AI", () =>
    pending(live, async () => {
      const health = await api.request(`${api.baseUrl}/health`);
      if (!health.ai_available)
        throw new Error(
          "The backend is running, but OPENAI_API_KEY is not configured. Add it to the server .env file first.",
        );
      const progress = await api.request(
        `${api.baseUrl}/students/${encodeURIComponent(state.data.student_id)}/progress`,
      );
      api.useMock = false;
      state.setMode("live", progress);
      renderProgress();
      document.querySelector("#mode-badge").textContent = "✦ LIVE AI CONNECTED";
      closeModal();
    }),
  );
  modal.append(
    offline,
    live,
    paragraph(
      "Live and offline assessment records are separate. Connecting loads your server progress; your explorer identity stays the same.",
      "source",
    ),
  );
};
// A restart is explicit so a learner cannot accidentally lose local progress.
const settingsButton = document.querySelector("#settings-button");
const showSettings = settingsButton.onclick;
settingsButton.onclick = () => {
  showSettings();
  modal.append(
    button(
      "Restart offline expedition",
      () => {
        showModal("Start again?", "OFFLINE EXPEDITION");
        modal.append(
          paragraph(
            "This resets offline XP, mission completion, and mastery in this browser. Your live server progress is unchanged.",
          ),
        );
        modal.append(button("Keep my progress", closeModal, "secondary"));
        modal.append(
          button("Reset offline progress", () => {
            api.useMock = true;
            state.setMode("offline", { xp: 0, completed: [], mastery: {} });
            renderProgress();
            document.querySelector("#mode-badge").textContent =
              "● OFFLINE EXPEDITION";
            closeModal();
          }),
        );
      },
      "secondary",
    ),
  );
};
