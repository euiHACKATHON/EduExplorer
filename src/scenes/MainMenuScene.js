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
    showModal("Your next discovery is waiting.", "WELCOME TO MARS");
    modal.append(
      paragraph(
        "The colony needs a curious mind. Join three crewmates, bring essential systems back online, and discover the science that makes life on Mars possible.",
      ),
      paragraph(
        "Three missions · Explore at your own pace · Ages 10+",
        "source",
      ),
      button("Begin expedition →", () => {
        closeModal();
        this.scene.start("CharacterSelectScene");
      }),
    );
  }
}
