import Phaser from "phaser";
import { WIDTH, HEIGHT } from "../config.js";
export class BootScene extends Phaser.Scene {
  constructor() {
    super("BootScene");
  }
  create() {
    for (const [key, color] of [
      ["amber", 0xefbe77],
      ["teal", 0x87c5bd],
      ["violet", 0xc1a7dc],
    ]) {
      const g = this.make.graphics({ x: 0, y: 0, add: false });
      g.fillStyle(0x231e25, 0.3).fillEllipse(20, 45, 34, 10);
      g.fillStyle(0x414650).fillRoundedRect(5, 19, 30, 21, 5);
      g.fillStyle(color).fillRoundedRect(9, 16, 22, 25, 6);
      g.fillStyle(0xece7d6).fillCircle(20, 12, 13);
      g.fillStyle(0x243842).fillRoundedRect(10, 5, 21, 13, 5);
      g.fillStyle(0x91c5c6).fillRect(12, 7, 7, 3);
      g.fillStyle(color).fillRect(9, 36, 8, 9).fillRect(23, 36, 8, 9);
      g.fillStyle(0x4b5355).fillRect(8, 43, 10, 5).fillRect(23, 43, 10, 5);
      g.generateTexture(key, 40, 50);
      g.destroy();
    }
    this.scene.start("MainMenuScene");
  }
}
