import Phaser from "phaser";
import {
  showModal,
  modal,
  paragraph,
  button,
  closeModal,
} from "../ui/DialogueUI.js";
import { state } from "../state/GameState.js";
export class CharacterSelectScene extends Phaser.Scene {
  constructor() {
    super("CharacterSelectScene");
  }
  create() {
    showModal("Choose your explorer", "CREW REGISTRATION");
    modal.append(paragraph("Same curiosity. Your own color."));
    for (const [key, label] of [
      ["amber", "◉  Amber / Pathfinder"],
      ["teal", "◉  Teal / Discoverer"],
      ["violet", "◉  Violet / Pioneer"],
    ])
      modal.append(
        button(
          label,
          () => {
            state.data.character = key;
            state.save();
            window.dispatchEvent(new Event("character-changed"));
            closeModal();
            this.scene.stop();
          },
          "choice",
        ),
      );
  }
}
