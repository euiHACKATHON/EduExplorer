import Phaser from "phaser";
import "./style.css";
import { WIDTH, HEIGHT, levels } from "./config.js";
import { BootScene } from "./scenes/BootScene.js";
import { MainMenuScene } from "./scenes/MainMenuScene.js";
import { CharacterSelectScene } from "./scenes/CharacterSelectScene.js";
import { MarsColonyScene } from "./scenes/MarsColonyScene.js";
import { renderProgress } from "./ui/ProgressUI.js";
import { api } from "./api/APIService.js";
import { state } from "./state/GameState.js";
import { applyTheme } from "./ui/Theme.js";
import { openMistakeJournal, renderJournalBadge } from "./ui/MistakeJournal.js";
import {
  openAITutor,
  setAITutorAvailable,
} from "./ui/AskAITutor.js";
import {
  showModal,
  modal,
  paragraph,
  button,
  field,
  pending,
  closeModal,
} from "./ui/DialogueUI.js";
applyTheme(state.data.character);
new Phaser.Game({
  type: Phaser.AUTO,
  parent: "game",
  width: WIDTH,
  height: HEIGHT,
  backgroundColor: "#070713",
  pixelArt: true,
  antialias: false,
  roundPixels: true,
  render: {
    antialias: false,
    pixelArt: true,
    roundPixels: true,
  },
  physics: { default: "arcade", arcade: { debug: false } },
  scale: { mode: Phaser.Scale.FIT, autoCenter: Phaser.Scale.CENTER_BOTH },
  scene: [BootScene, MainMenuScene, CharacterSelectScene, MarsColonyScene],
});
renderProgress();
renderJournalBadge();
document.querySelector("#journal-button").onclick = openMistakeJournal;
document.querySelector("#ask-ai-button").onclick = () => openAITutor();
const setConnectionUI = (live) => {
  document.querySelector("#mode-badge").innerHTML = `<i></i> ${live ? "LIVE AI" : "OFFLINE"}`;
  setAITutorAvailable(live);
};
// Switching between offline/live profiles can leave the on-screen world
// pointed at a level that isn't unlocked for the *new* profile (e.g. an
// offline save that cleared all 3 worlds, then a brand-new live account
// with nothing unlocked past World 1). Snap back to the first world that
// profile hasn't finished yet -- or the last one, if it's finished all of
// them -- so the player is never stranded looking at a locked world.
const goToValidLevel = () => {
  const firstOpen = levels.findIndex(
    (item) => !state.data.completed.includes(item.mission),
  );
  const target = firstOpen < 0 ? levels.length - 1 : firstOpen;
  window.dispatchEvent(new CustomEvent("enter-level", { detail: target }));
};
setConnectionUI(false);
document.querySelector("#settings-button").onclick = () => {
  showModal("Expedition settings", "CONNECTION");
  modal.append(
    paragraph(
      "Offline mode is ready to play. Live AI uses the FastAPI service and its server-side Groq key.",
    ),
  );
  const offline = button(
    "Use offline lessons",
    () => {
      api.useMock = true;
      state.setMode("offline");
      renderProgress();
      setConnectionUI(false);
      renderJournalBadge();
      goToValidLevel();
      closeModal();
    },
    "secondary",
  );
  const finishConnectingLive = (progress) => {
    api.useMock = false;
    state.setMode("live", progress);
    renderProgress();
    setConnectionUI(true);
    renderJournalBadge();
    goToValidLevel();
    closeModal();
  };
  // Uses whatever token api already holds (set at login/register, or
  // restored from localStorage on a prior visit). Throws -- with the token
  // now cleared -- if the server rejects it as missing/expired.
  const connectWithToken = async () => {
    const health = await api.request(`${api.baseUrl}/health`);
    if (!health.ai_available)
      throw new Error(
        "The backend is running, but GROQ_API_KEY is not configured. Add it to the server .env file first.",
      );
    const progress = await api.getProgress();
    finishConnectingLive(progress);
  };
  const showAuthForm = () => {
    let mode = "login";
    const wrap = document.createElement("div");
    wrap.className = "auth-form";
    const render = () => {
      wrap.replaceChildren();
      const tabs = document.createElement("div");
      tabs.className = "auth-tabs";
      tabs.append(
        button(
          "Sign in",
          () => {
            mode = "login";
            render();
          },
          mode === "login" ? "primary" : "secondary",
        ),
        button(
          "Create explorer ID",
          () => {
            mode = "register";
            render();
          },
          mode === "register" ? "primary" : "secondary",
        ),
      );
      const idField = field("Explorer ID", {
        placeholder: "e.g. amber_star",
        autocomplete: "username",
      });
      const passField = field("Password", {
        type: "password",
        autocomplete: mode === "register" ? "new-password" : "current-password",
      });
      const nameField = field("Display name", { placeholder: "e.g. Amber" });
      const gradeField = field("Grade level (optional)", {
        placeholder: "e.g. 7th grade",
      });
      const idPassRow = document.createElement("div");
      idPassRow.className = "field-row";
      idPassRow.append(idField, passField);
      wrap.append(tabs, idPassRow);
      if (mode === "register") {
        const nameGradeRow = document.createElement("div");
        nameGradeRow.className = "field-row";
        nameGradeRow.append(nameField, gradeField);
        wrap.append(nameGradeRow);
      }
      const submit = button(
        mode === "register" ? "Create ID & connect" : "Sign in & connect",
        () =>
          pending(submit, async () => {
            const student_id = idField.input.value.trim();
            const password = passField.input.value;
            if (!student_id || !password)
              throw new Error("Enter an explorer ID and password.");
            if (mode === "register") {
              await api.register({
                student_id,
                password,
                display_name: nameField.input.value.trim() || student_id,
                grade_level: gradeField.input.value.trim(),
              });
            } else {
              await api.login({ student_id, password });
            }
            // The account's chosen ID becomes this browser's identity going
            // forward, in both live and offline play.
            state.data.student_id = student_id;
            state.save();
            await connectWithToken();
          }),
      );
      wrap.append(submit);
    };
    render();
    modal.append(wrap);
  };
  const live = button("Connect to live AI", () =>
    pending(live, async () => {
      if (!api.token) {
        showAuthForm();
        return;
      }
      try {
        await connectWithToken();
      } catch (e) {
        if (api.token) throw e; // a real failure, e.g. backend unreachable
        modal.append(paragraph(e.message, "error"));
        showAuthForm();
      }
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
  if (!api.useMock) {
    modal.append(
      button(
        "Log out of live AI",
        () => {
          api.clearToken();
          api.useMock = true;
          state.setMode("offline");
          renderProgress();
          renderJournalBadge();
          setConnectionUI(false);
          goToValidLevel();
          closeModal();
        },
        "secondary",
      ),
    );
  }
  modal.append(
    button(
      "Restart offline expedition",
      () => {
        showModal("Start again?", "OFFLINE EXPEDITION");
        modal.append(
          paragraph(
            "This resets offline XP, mission completion, mastery, and the learning journal in this browser. Your live server progress is unchanged.",
          ),
        );
        modal.append(button("Keep my progress", closeModal, "secondary"));
        modal.append(
          button("Reset offline progress", () => {
            api.useMock = true;
            state.setMode("offline", {
              xp: 0,
              completed: [],
              mastery: {},
              mistakes: [],
            });
            renderProgress();
            renderJournalBadge();
            setConnectionUI(false);
            goToValidLevel();
            closeModal();
          }),
        );
      },
      "secondary",
    ),
  );
};