import Phaser from "phaser";
import { WIDTH, HEIGHT, crew } from "../config.js";
import { Player } from "../entities/Player.js";
import { NPC } from "../entities/NPC.js";
import { state } from "../state/GameState.js";
import { modal, dialogue } from "../ui/DialogueUI.js";
export class MarsColonyScene extends Phaser.Scene {
  constructor() {
    super("MarsColonyScene");
  }
  create() {
    this.cameras.main.setBackgroundColor("#a96347");
    const g = this.add.graphics();
    g.fillStyle(0xb87451).fillRect(0, 0, WIDTH, HEIGHT);
    const rng = new Phaser.Math.RandomDataGenerator(["arcadia"]);
    for (let i = 0; i < 260; i++) {
      g.fillStyle(rng.pick([0xc17b54, 0xa45e43, 0xd18c60]), 0.7);
      g.fillEllipse(
        rng.between(0, WIDTH),
        rng.between(0, HEIGHT),
        rng.between(3, 15),
        rng.between(2, 5),
      );
    }
    const path = (x, y, w, h) => {
      g.fillStyle(0xd99868, 0.7).fillRoundedRect(x, y, w, h, 20);
    };
    path(300, 350, 550, 55);
    path(510, 370, 55, 200);
    path(550, 510, 260, 45);
    path(790, 295, 45, 95);
    for (const [x, y, rx, ry] of [
      [90, 110, 85, 40],
      [995, 545, 100, 50],
      [1030, 115, 120, 45],
      [160, 550, 60, 27],
    ]) {
      g.fillStyle(0x98573f, 0.6).fillEllipse(x, y, rx, ry);
      g.lineStyle(5, 0xd28c60, 0.7).strokeEllipse(x, y - 3, rx, ry);
      g.fillStyle(0xa56246).fillEllipse(x + 3, y + 4, rx * 0.75, ry * 0.65);
    }
    const building = (x, y, w, h, label, color = 0xbfc6bb) => {
      g.fillStyle(0x583c32, 0.25).fillRoundedRect(x + 15, y + 18, w, h, 20);
      g.fillStyle(0x535e5c).fillRoundedRect(x, y + 12, w, h, 18);
      g.fillStyle(color).fillRoundedRect(x, y, w, h - 12, 18);
      g.lineStyle(3, 0xe4ddc2).strokeRoundedRect(
        x + 5,
        y + 5,
        w - 10,
        h - 22,
        14,
      );
      g.fillStyle(0x576e70).fillRoundedRect(x + 25, y + 22, w - 50, 25, 7);
      g.lineStyle(2, 0x83a8a4);
      for (let xx = x + 40; xx < x + w - 25; xx += 25)
        g.lineBetween(xx, y + 23, xx, y + 46);
      g.fillStyle(0x445555).fillRect(x + w / 2 - 18, y + h - 29, 36, 29);
      this.add
        .text(x + w / 2, y - 17, label, {
          fontSize: 11,
          fontFamily: "monospace",
          color: "#ffe6bd",
          letterSpacing: 2,
        })
        .setOrigin(0.5);
    };
    building(190, 180, 230, 135, "01 / RESEARCH HAB");
    building(735, 135, 205, 112, "02 / POWER STATION", 0xc3bca4);
    building(625, 415, 200, 88, "03 / BIO DOME", 0xa4b79a);
    // Solar array and greenhouse glazing are drawn as native game assets.
    for (let row = 0; row < 2; row++)
      for (let col = 0; col < 3; col++) {
        const x = 925 + col * 48,
          y = 285 + row * 46;
        g.fillStyle(0x503d32).fillRect(x + 20, y + 25, 5, 22);
        g.fillStyle(0x344c5e).fillRect(x, y, 42, 30);
        g.lineStyle(1, 0x91b1b9).strokeRect(x, y, 42, 30);
        g.lineBetween(x + 21, y, x + 21, y + 30);
        g.lineBetween(x, y + 15, x + 42, y + 15);
      }
    g.fillStyle(0x77a599, 0.7).fillRoundedRect(644, 425, 163, 47, 15);
    g.lineStyle(3, 0xdce0bd);
    for (let i = 0; i < 5; i++)
      g.lineBetween(655 + i * 33, 426, 655 + i * 33, 470);
    for (let i = 0; i < 5; i++) {
      g.fillStyle(0x637d46).fillCircle(660 + i * 30, 454, 9);
    }
    // Rover Beta.
    for (const x of [450, 500])
      for (const y of [266, 301])
        g.fillStyle(0x3d403c).fillRoundedRect(x, y, 15, 16, 4);
    g.fillStyle(0xd8c9a3).fillRoundedRect(447, 267, 69, 43, 10);
    g.fillStyle(0x677e7d).fillRect(462, 274, 30, 18);
    g.lineStyle(3, 0xebe0bd).lineBetween(494, 266, 494, 237);
    g.fillStyle(0x85bfc0).fillCircle(494, 236, 6);
    // Landing pad and flags.
    g.lineStyle(2, 0xe6b087, 0.7).strokeCircle(365, 515, 58);
    g.lineStyle(2, 0xe6b087, 0.4).strokeCircle(365, 515, 66);
    this.add
      .text(365, 515, "H", { fontSize: 50, color: "#e9b58a" })
      .setOrigin(0.5);
    g.lineStyle(4, 0xd7c6a0).lineBetween(540, 180, 540, 240);
    g.fillStyle(0xe4b875).fillTriangle(542, 182, 579, 193, 542, 207);
    this.add.text(40, 35, "ARCADIA BASE", {
      fontFamily: "monospace",
      fontSize: 14,
      color: "#f2cea4",
      letterSpacing: 3,
    });
    this.add.text(40, 58, "ELEV. −2,410 M  /  TEMP. −42°C", {
      fontFamily: "monospace",
      fontSize: 10,
      color: "#e4b28c",
    });
    this.player = new Player(this, 450, 385, state.data.character);
    this.npcs = crew.map((c, i) => new NPC(this, c, i));
    this.npcs.forEach((n) =>
      n.on("pointerdown", () => this.navigate(n.info.id)),
    );
    this.input.on("pointerdown", (p) => {
      if (modal.open || p.currentlyOver?.length) return;
      this.player.target = { x: p.worldX, y: p.worldY };
    });
    this.prompt = this.add
      .text(0, 0, "E  Talk to crewmate", {
        fontSize: 13,
        fontFamily: "Arial",
        color: "#263435",
        backgroundColor: "#f6d69e",
        padding: { x: 12, y: 8 },
      })
      .setOrigin(0.5)
      .setDepth(1000)
      .setVisible(false);
    this.keyE = this.input.keyboard.addKey("E");
    this.keyEsc = this.input.keyboard.addKey("ESC");
    this.onNavigate = (e) => this.navigate(e.detail);
    this.onCharacter = () => this.player.setTexture(state.data.character);
    window.addEventListener("navigate-crew", this.onNavigate);
    window.addEventListener("character-changed", this.onCharacter);
    this.events.once("shutdown", () => {
      window.removeEventListener("navigate-crew", this.onNavigate);
      window.removeEventListener("character-changed", this.onCharacter);
    });
    this.systemLabels = crew.map((c) =>
      this.add
        .text(c.x, c.y + 59, "", {
          fontSize: 10,
          color: "#e4f2bd",
          fontFamily: "monospace",
        })
        .setOrigin(0.5)
        .setDepth(901),
    );
  }
  navigate(id) {
    if (modal.open) return;
    const npc = this.npcs.find((n) => n.info.id === id);
    this.player.target = { x: npc.x, y: npc.y + 43 };
    this.autoNPC = id;
  }
  update() {
    this.player.update(modal.open);
    this.systemLabels.forEach((label, i) =>
      label.setText(
        state.data.completed.includes(crew[i].mission) ? "✓ SYSTEM ONLINE" : "",
      ),
    );
    const near = this.npcs.find(
      (n) => Phaser.Math.Distance.BetweenPoints(this.player, n) < 65,
    );
    this.prompt.setVisible(Boolean(near) && !modal.open);
    if (near) {
      this.prompt.setPosition(near.x, near.y - 72);
      if (
        !modal.open &&
        (Phaser.Input.Keyboard.JustDown(this.keyE) ||
          (this.autoNPC === near.info.id && !this.player.target))
      ) {
        this.autoNPC = null;
        this.player.body.stop();
        dialogue(near.info);
      }
    }
  }
}
