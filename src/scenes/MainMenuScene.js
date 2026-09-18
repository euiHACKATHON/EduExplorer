import Phaser from "phaser";
import {
  showModal,
  modal,
  paragraph,
  button,
  closeModal,
} from "../ui/DialogueUI.js";
export class MainMenuScene extends Phaser.Scene {
  constructor() {
    super("MainMenuScene");
  }
  create() {
    this.scene.start("MarsColonyScene");
    showModal("The observatory has lost contact.", "EXPEDITION BRIEF");
    modal.append(
      paragraph(
        "Three remote worlds have gone dark. Travel to each station, help its crew solve the failure, and bring the observatory network back online.",
      ),
      paragraph(
        "Three worlds. Three science missions. One route home.",
        "source",
      ),
      button("Begin expedition", () => {
        closeModal();
        this.scene.start("CharacterSelectScene");
      }),
    );
  }
}
