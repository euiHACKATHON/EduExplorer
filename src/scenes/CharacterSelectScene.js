import Phaser from "phaser";
import {
  showModal,
  modal,
  paragraph,
  button,
  closeModal,
} from "../ui/DialogueUI.js";
import { state } from "../state/GameState.js";
import { applyTheme } from "../ui/Theme.js";
export class CharacterSelectScene extends Phaser.Scene {
  constructor() {
    super("CharacterSelectScene");
  }
  create() {
    showModal("Choose your starfarer", "CELESTIAL ATTUNEMENT");
    modal.append(paragraph("Every traveler carries a different cosmic light."));
    for (const [key, label] of [
      ["amber", "☉  Solar / The Pathfinder"],
      ["teal", "☽  Lunar / The Seer"],
      ["violet", "✦  Nebula / The Dreamer"],
    ]) {
      const choice = button(
        label,
        () => {
          state.data.character = key;
          state.save();
          applyTheme(key);
          window.dispatchEvent(new Event("character-changed"));
          closeModal();
          this.scene.stop();
        },
        "choice",
      );
      choice.dataset.theme = key;
      choice.setAttribute("aria-pressed", String(state.data.character === key));
      if (state.data.character === key) choice.classList.add("selected");
      modal.append(choice);
    }
  }
}
