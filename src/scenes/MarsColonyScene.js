import Phaser from "phaser";
import { AudioManager } from "../audio/AudioManager.js";
import { WIDTH, HEIGHT, crew, levels } from "../config.js";
import { Player } from "../entities/Player.js";
import { NPC } from "../entities/NPC.js";
import { state } from "../state/GameState.js";
import { modal, dialogue } from "../ui/DialogueUI.js";
import { drawPixelSigil } from "../ui/PixelSigil.js";

const STAR_MAPS = [
  [
    [0, 1],
    [1, 2],
    [2, 3],
    [2, 4],
  ],
  [
    [0, 1],
    [1, 2],
    [2, 3],
    [3, 4],
    [2, 5],
  ],
  [
    [0, 1],
    [1, 2],
    [2, 3],
    [1, 4],
    [4, 5],
  ],
];

export class MarsColonyScene extends Phaser.Scene {
  constructor() {
    super("MarsColonyScene");
  }

  create(data = {}) {
    this.transitioning = false;
    this.autoNPC = false;
    this.pendingCelebration = false;
    const firstOpen = levels.findIndex(
      (level) =>
        state.isMissionUnlocked(level.mission) &&
        !state.data.completed.includes(level.mission),
    );
    this.levelIndex = Phaser.Math.Clamp(
      data.levelIndex ?? (firstOpen < 0 ? 2 : firstOpen),
      0,
      levels.length - 1,
    );
    this.level = levels[this.levelIndex];
    this.keeper = { ...crew[this.levelIndex], x: 820, y: 382 };
    this.cameras.main.setBackgroundColor(this.level.sky);
    this.drawRealm();
    this.player = new Player(this, 245, 505, state.data.character);
    this.npc = new NPC(this, this.keeper, this.levelIndex);
    this.npc.on("pointerdown", () => this.navigate());
    this.prompt = this.add
      .text(0, 0, "E  Begin celestial trial", {
        fontSize: 13,
        fontFamily: "Arial",
        color: "#10131f",
        backgroundColor: `#${this.level.accent.toString(16).padStart(6, "0")}`,
        padding: { x: 14, y: 9 },
      })
      .setOrigin(0.5)
      .setDepth(1000)
      .setVisible(false);
    this.keyE = this.input.keyboard.addKey("E");
    this.input.on("pointerdown", (pointer) => {
      if (modal.open || pointer.currentlyOver?.length) return;
      this.player.target = { x: pointer.worldX, y: pointer.worldY };
    });
    this.onNavigate = (event) => {
      const index = crew.findIndex((member) => member.id === event.detail);
      if (index >= 0) this.transportTo(index);
    };
    this.onEnterLevel = (event) => this.transportTo(event.detail);
    this.onCharacter = () => this.player.setTexture(state.data.character);
    this.onComplete = (event) => {
      if (event.detail === this.level.mission) this.pendingCelebration = true;
    };
    window.addEventListener("navigate-crew", this.onNavigate);
    window.addEventListener("enter-level", this.onEnterLevel);
    window.addEventListener("character-changed", this.onCharacter);
    window.addEventListener("mission-completed", this.onComplete);
    this.events.once("shutdown", () => {
      AudioManager.stopAmbient();
      window.removeEventListener("navigate-crew", this.onNavigate);
      window.removeEventListener("enter-level", this.onEnterLevel);
      window.removeEventListener("character-changed", this.onCharacter);
      window.removeEventListener("mission-completed", this.onComplete);
    });
    window.dispatchEvent(
      new CustomEvent("realm-changed", { detail: this.levelIndex }),
    );
    if (data.transport) this.playArrival();
    AudioManager.playAmbient(this.levelIndex);
    if (this.levelIndex === 0) this.scheduleGust();
  }

  drawRealm() {
    const g = this.add.graphics().setDepth(0);
    g.fillStyle(this.level.sky).fillRect(0, 0, WIDTH, HEIGHT);
    this.dustClouds = this.add.graphics().setDepth(1);
    this.starfield = this.add.container(0, 0).setDepth(2);
    const stars = this.add.graphics();
    this.starfield.add(stars);
    const rng = new Phaser.Math.RandomDataGenerator([
      `zodiac-${this.levelIndex}`,
    ]);
    for (let i = 0; i < 145; i++) {
      stars.fillStyle(
        rng.pick([0xffffff, this.level.accent, 0xbac9ff]),
        rng.realInRange(0.35, 0.95),
      );
      stars.fillCircle(
        rng.between(0, WIDTH),
        rng.between(0, 380),
        rng.realInRange(0.7, 2.4),
      );
    }
    for (let i = 0; i < 20; i++) {
      const star = this.add.circle(
        rng.between(12, WIDTH - 12),
        rng.between(12, 320),
        rng.realInRange(1, 2),
        0xffffff,
        0.85,
      );
      this.starfield.add(star);
      this.tweens.add({
        targets: star,
        alpha: 0.2,
        duration: rng.between(1300, 2900),
        delay: rng.between(0, 1800),
        yoyo: true,
        repeat: -1,
        ease: "Sine.easeInOut",
      });
    }
    for (let i = 0; i < 7; i++)
      this.dustClouds
        .fillStyle(this.level.accent, 0.025)
        .fillCircle(
          rng.between(80, 1040),
          rng.between(60, 330),
          rng.between(70, 190),
        );
    const foreground = this.add.graphics().setDepth(3);
    foreground.fillStyle(this.level.ground).fillEllipse(560, 680, 1320, 390);
    foreground.fillStyle(0x050812, 0.34).fillEllipse(560, 665, 1150, 260);
    foreground.lineStyle(2, this.level.accent, 0.16);
    for (let r = 80; r < 470; r += 65)
      foreground.strokeEllipse(560, 585, r * 2.2, r * 0.48);
    this.sigil = this.add.graphics().setDepth(4);
    this.refreshSigil();
    this.drawConstellation(foreground);
    this.drawLandmark(foreground);
    this.add
      .text(
        560,
        628,
        `CURRENT TRIAL  ·  ${this.level.objective.toUpperCase()}`,
        {
          fontFamily: "monospace",
          fontSize: 11,
          color: "#f5f2ff",
          letterSpacing: 2,
        },
      )
      .setOrigin(0.5)
      .setDepth(5);
  }

  drawConstellation(g) {
    const points = Array.from({ length: 6 }, (_, i) => ({
      x: 720 + [0, 55, 115, 180, 90, 205][i],
      y: 95 + [70, 15, 75, 25, 135, 125][i],
    }));
    g.lineStyle(2, this.level.accent, 0.38);
    STAR_MAPS[this.levelIndex].forEach(([a, b]) =>
      g.lineBetween(points[a].x, points[a].y, points[b].x, points[b].y),
    );
    points.forEach((point, i) => {
      g.fillStyle(0xffffff, 0.95).fillCircle(point.x, point.y, i === 2 ? 6 : 4);
      g.lineStyle(1, this.level.accent, 0.4).strokeCircle(point.x, point.y, 10);
    });
  }

  drawLandmark(g) {
    if (this.levelIndex === 0) {
      // Rover service hangar: broad, low architecture grounded in the dunes.
      g.fillStyle(0x130f19, 0.96).fillRoundedRect(390, 350, 320, 150, 18);
      g.fillStyle(0x2c1e29, 1).fillRoundedRect(414, 374, 272, 126, 12);
      g.lineStyle(3, this.level.accent, 0.72).strokeRoundedRect(
        390,
        350,
        320,
        150,
        18,
      );
      g.lineStyle(2, this.level.accent, 0.3);
      for (let x = 432; x < 686; x += 42) g.lineBetween(x, 374, x, 496);
      g.fillStyle(0x090b12, 1).fillRoundedRect(474, 398, 150, 102, 7);
      for (const x of [443, 660]) {
        const light = this.add.circle(x, 382, 6, 0xffdfaa).setDepth(4);
        this.tweens.add({
          targets: light,
          alpha: 0.6,
          duration: 1200,
          yoyo: true,
          repeat: -1,
          ease: "Sine.easeInOut",
        });
      }
      g.fillStyle(0x17131c, 1).fillRect(365, 304, 18, 96);
      g.lineStyle(3, this.level.accent, 0.65).lineBetween(374, 304, 418, 268);
      g.fillStyle(this.level.accent, 0.85).fillCircle(421, 266, 7);
      g.lineStyle(2, this.level.accent, 0.22).strokeCircle(421, 266, 21);
    } else if (this.levelIndex === 1) {
      this.rings = this.add.container(545, 405).setDepth(4);
      for (let i = 0; i < 4; i++) {
        const ring = this.add
          .ellipse(0, 0, 275 - i * 48, 145 - i * 18)
          .setStrokeStyle(5, this.level.accent, 0.55);
        this.rings.add(ring);
      }
      this.tweens.add({
        targets: this.rings,
        rotation: Math.PI * 2,
        duration: 314159,
        repeat: -1,
        ease: "Linear",
      });
      g.fillStyle(0xffffff, 0.85).fillCircle(545, 405, 18);
      g.lineStyle(3, 0xffffff, 0.65).lineBetween(545, 260, 545, 548);
    } else {
      g.fillStyle(0x0d1816, 0.85).fillRoundedRect(420, 330, 270, 175, 70);
      g.lineStyle(4, this.level.accent, 0.6).strokeRoundedRect(
        420,
        330,
        270,
        175,
        70,
      );
      for (let i = 0; i < 8; i++) {
        const x = 450 + i * 30;
        const plant = this.add.graphics({ x, y: 475 }).setDepth(4);
        plant
          .lineStyle(3, 0x89d56f, 0.7)
          .lineBetween(0, 0, 0, -70 - (i % 3) * 18);
        plant
          .fillStyle(this.level.accent, 0.68)
          .fillCircle(0, -75 - (i % 3) * 18, 9);
        plant.angle = -3;
        this.tweens.add({
          targets: plant,
          angle: 3,
          duration: 1800 + i * 80,
          delay: i * 130,
          yoyo: true,
          repeat: -1,
          ease: "Sine.easeInOut",
        });
      }
    }
  }

  refreshSigil() {
    const completed = state.data.completed.includes(this.level.mission);
    this.sigilComplete = completed;
    const g = this.sigil.clear();
    g.lineStyle(7, this.level.accent, completed ? 1 : 0.55).strokeCircle(
      180,
      500,
      74,
    );
    g.lineStyle(2, 0xffffff, completed ? 0.95 : 0.35).strokeCircle(
      180,
      500,
      58,
    );
    g.fillStyle(this.level.accent, completed ? 0.3 : 0.09).fillCircle(
      180,
      500,
      55,
    );
    g.fillStyle(completed ? 0xffffff : this.level.accent, completed ? 1 : 0.65);
    drawPixelSigil(g, this.level, 180, 500, 8);
  }

  celebrateMission() {
    this.pendingCelebration = false;
    this.refreshSigil();
    AudioManager.celebrate();
    const color = Phaser.Display.Color.IntegerToColor(this.level.accent);
    this.cameras.main.flash(300, color.red, color.green, color.blue);
    for (let i = 0; i < 24; i++) {
      const angle = (i * Math.PI * 2) / 24;
      const spark = this.add
        .circle(this.player.x, this.player.y, 3, this.level.accent)
        .setDepth(1100);
      this.tweens.add({
        targets: spark,
        x: spark.x + Math.cos(angle) * 90,
        y: spark.y + Math.sin(angle) * 70,
        alpha: 0,
        scale: 0.2,
        duration: 850,
        onComplete: () => spark.destroy(),
      });
    }
    this.tweens.add({
      targets: this.sigil,
      alpha: 0.45,
      duration: 220,
      yoyo: true,
      repeat: 2,
    });
  }

  scheduleGust() {
    this.time.delayedCall(Phaser.Math.Between(30000, 60000), () => {
      if (!this.transitioning && !modal.open) {
        AudioManager.dustGust();
        for (let i = 0; i < 28; i++) {
          const dust = this.add
            .ellipse(
              -60 - i * 12,
              Phaser.Math.Between(490, 610),
              Phaser.Math.Between(12, 30),
              2,
              this.level.accent,
              0.15,
            )
            .setDepth(6);
          this.tweens.add({
            targets: dust,
            x: WIDTH + 60,
            alpha: 0,
            duration: Phaser.Math.Between(1900, 2800),
            onComplete: () => dust.destroy(),
          });
        }
      }
      this.scheduleGust();
    });
  }

  playArrival() {
    AudioManager.arrival();
    this.transitioning = true;
    const layer = this.add.container(0, 0).setDepth(5000);
    const veil = this.add.rectangle(
      WIDTH / 2,
      HEIGHT / 2,
      WIDTH,
      HEIGHT,
      0x02040d,
    );
    const glow = this.add
      .circle(WIDTH / 2, HEIGHT / 2 + 20, 178, this.level.accent, 0.12)
      .setScale(3.8);
    const planet = this.add
      .circle(WIDTH / 2, HEIGHT / 2 + 20, 112, this.level.ground)
      .setStrokeStyle(5, this.level.accent, 0.9)
      .setScale(3.8);
    const horizon = this.add
      .ellipse(WIDTH / 2, HEIGHT / 2 + 3, 182, 32, this.level.accent, 0.16)
      .setScale(3.8);
    const arrivalLabel = this.add
      .text(WIDTH / 2, 112, "DESTINATION REACHED", {
        fontFamily: "monospace",
        fontSize: 11,
        color: `#${this.level.accent.toString(16).padStart(6, "0")}`,
        letterSpacing: 5,
      })
      .setOrigin(0.5)
      .setAlpha(0);
    const title = this.add
      .text(WIDTH / 2, 154, this.level.realm, {
        align: "center",
        fontFamily: "monospace",
        fontSize: 44,
        color: "#ffffff",
        letterSpacing: 9,
      })
      .setOrigin(0.5)
      .setAlpha(0);
    const subtitle = this.add
      .text(WIDTH / 2, 211, this.level.subtitle.toUpperCase(), {
        fontFamily: "monospace",
        fontSize: 11,
        color: "#dce8ff",
        letterSpacing: 3,
      })
      .setOrigin(0.5)
      .setAlpha(0);
    layer.add([veil, glow, planet, horizon, arrivalLabel, title, subtitle]);
    this.tweens.add({
      targets: [glow, planet, horizon],
      scale: 1,
      duration: 1250,
      ease: "Cubic.easeOut",
    });
    this.tweens.add({
      targets: [arrivalLabel, title, subtitle],
      alpha: 1,
      y: "-=8",
      delay: 480,
      duration: 520,
      ease: "Sine.easeOut",
    });
    this.tweens.add({
      targets: layer,
      alpha: 0,
      delay: 1450,
      duration: 700,
      ease: "Sine.easeInOut",
      onComplete: () => {
        layer.destroy(true);
        this.transitioning = false;
      },
    });
  }

  playCelestialTransit(index) {
    if (this.pendingCelebration) this.celebrateMission();
    const destination = levels[index];
    this.transitioning = true;
    this.player.body.stop();
    this.prompt.setVisible(false);

    const layer = this.add.container(0, 0).setDepth(5000);
    const space = this.add
      .rectangle(WIDTH / 2, HEIGHT / 2, WIDTH, HEIGHT, 0x02040d, 0)
      .setInteractive();
    layer.add(space);
    this.tweens.add({ targets: space, fillAlpha: 1, duration: 350 });

    const backdrop = this.add.graphics();
    const rng = new Phaser.Math.RandomDataGenerator([`jump-${index}`]);
    for (let i = 0; i < 90; i++) {
      backdrop.fillStyle(
        i % 8 === 0 ? destination.accent : 0xffffff,
        rng.realInRange(0.18, 0.7),
      );
      backdrop.fillCircle(
        rng.between(10, WIDTH - 10),
        rng.between(40, HEIGHT - 40),
        rng.realInRange(0.5, 1.6),
      );
    }
    backdrop
      .fillStyle(this.level.ground, 0.75)
      .fillCircle(20, HEIGHT + 40, 185);
    backdrop
      .fillStyle(destination.ground, 0.65)
      .fillCircle(WIDTH + 35, 70, 210);
    backdrop
      .lineStyle(3, destination.accent, 0.35)
      .strokeCircle(WIDTH + 35, 70, 218);
    layer.add(backdrop);

    const points = [
      { x: 112, y: 535 },
      { x: 290, y: 430 },
      { x: 485, y: 505 },
      { x: 675, y: 350 },
      { x: 864, y: 435 },
      { x: 1040, y: 250 },
    ];
    const steppingStars = points.map((point, step) => {
      const star = this.add.container(point.x, point.y);
      const glow = this.add.circle(
        0,
        0,
        step === points.length - 1 ? 45 : 31,
        step < 2 ? this.level.accent : destination.accent,
        0.1,
      );
      const core = this.add.star(
        0,
        0,
        6,
        step === points.length - 1 ? 12 : 8,
        step === points.length - 1 ? 28 : 20,
        step < 2 ? this.level.accent : destination.accent,
        0.95,
      );
      const light = this.add.circle(0, 0, 4, 0xffffff, 1);
      star.add([glow, core, light]);
      layer.add(star);
      this.tweens.add({
        targets: glow,
        scale: 1.28,
        alpha: 0.2,
        duration: 700 + step * 90,
        yoyo: true,
        repeat: -1,
      });
      return { star, glow, core, point };
    });

    const route = this.add.graphics();
    route.lineStyle(1, 0xffffff, 0.09);
    for (let i = 0; i < points.length - 1; i++)
      route.lineBetween(
        points[i].x,
        points[i].y,
        points[i + 1].x,
        points[i + 1].y,
      );
    layer.addAt(route, 2);

    const title = this.add
      .text(WIDTH / 2, 74, `NEXT WORLD  ·  ${destination.realm}`, {
        fontFamily: "Arial",
        fontSize: 13,
        color: "#ffffff",
        letterSpacing: 3,
      })
      .setOrigin(0.5)
      .setAlpha(0);
    const subtitle = this.add
      .text(WIDTH / 2, 103, destination.title, {
        fontFamily: "Arial",
        fontSize: 25,
        color: `#${destination.accent.toString(16).padStart(6, "0")}`,
      })
      .setOrigin(0.5)
      .setAlpha(0);
    layer.add([title, subtitle]);

    const traveler = this.add
      .sprite(points[0].x, points[0].y - 34, state.data.character)
      .setScale(1.65)
      .setOrigin(0.5, 1);
    const shadow = this.add.ellipse(
      points[0].x,
      points[0].y + 2,
      38,
      10,
      0x000000,
      0.38,
    );
    layer.add([shadow, traveler]);

    const burstAt = ({ x, y }, color) => {
      for (let i = 0; i < 10; i++) {
        const spark = this.add.circle(
          x,
          y,
          rng.realInRange(1.2, 3),
          color,
          0.9,
        );
        layer.add(spark);
        const angle = (Math.PI * 2 * i) / 10;
        this.tweens.add({
          targets: spark,
          x: x + Math.cos(angle) * rng.between(25, 52),
          y: y + Math.sin(angle) * rng.between(18, 38),
          alpha: 0,
          scale: 0.2,
          duration: 360,
          onComplete: () => spark.destroy(),
        });
      }
    };

    const jumpTo = (step) => {
      if (step >= points.length) {
        this.tweens.add({
          targets: [title, subtitle],
          alpha: 1,
          duration: 360,
        });
        this.time.delayedCall(720, () =>
          this.scene.restart({ levelIndex: index, transport: true }),
        );
        return;
      }
      const from = points[step - 1];
      const to = points[step];
      shadow.setAlpha(0.12);
      traveler.setFlipX(to.x < from.x);
      this.tweens.addCounter({
        from: 0,
        to: 1,
        duration: step === points.length - 1 ? 620 : 470,
        ease: "Sine.easeInOut",
        onUpdate: (tween) => {
          const t = tween.getValue();
          traveler.x = Phaser.Math.Linear(from.x, to.x, t);
          traveler.y =
            Phaser.Math.Linear(from.y - 34, to.y - 34, t) -
            Math.sin(Math.PI * t) * 95;
          shadow.x = traveler.x;
          shadow.y = Phaser.Math.Linear(from.y + 2, to.y + 2, t);
          traveler.setAngle(Math.sin(Math.PI * 2 * t) * 7);
        },
        onComplete: () => {
          traveler.setAngle(0);
          shadow.setAlpha(0.38);
          burstAt(to, step < 2 ? this.level.accent : destination.accent);
          AudioManager.landing(step);
          this.tweens.add({
            targets: steppingStars[step].star,
            scale: 1.3,
            duration: 110,
            yoyo: true,
          });
          this.cameras.main.shake(90, 0.002);
          this.time.delayedCall(90, () => jumpTo(step + 1));
        },
      });
    };

    this.time.delayedCall(420, () => {
      AudioManager.travelWhoosh();
      burstAt(points[0], this.level.accent);
      jumpTo(1);
    });
  }

  transportTo(index) {
    if (
      !Number.isInteger(index) ||
      index === this.levelIndex ||
      this.transitioning ||
      !state.isMissionUnlocked(levels[index]?.mission)
    )
      return;
    this.playCelestialTransit(index);
  }

  navigate() {
    if (modal.open || this.transitioning) return;
    this.player.target = { x: this.npc.x, y: this.npc.y + 45 };
    this.autoNPC = true;
  }

  update(_time, delta) {
    this.player.update(modal.open || this.transitioning, delta);
    this.npc.facePlayer(this.player.x);
    this.starfield.setPosition(
      (WIDTH / 2 - this.player.x) * 0.012,
      (HEIGHT / 2 - this.player.y) * 0.008,
    );
    this.dustClouds.setPosition(
      (WIDTH / 2 - this.player.x) * 0.005,
      (HEIGHT / 2 - this.player.y) * 0.003,
    );
    if (
      this.sigilComplete !== state.data.completed.includes(this.level.mission)
    )
      this.refreshSigil();
    if (this.pendingCelebration && !modal.open && !this.transitioning)
      this.celebrateMission();
    const near = Phaser.Math.Distance.BetweenPoints(this.player, this.npc) < 70;
    const showPrompt = near && !modal.open && !this.transitioning;
    if (showPrompt && !this.prompt.visible) AudioManager.blip();
    this.prompt.setVisible(showPrompt).setPosition(this.npc.x, this.npc.y - 78);
    if (
      near &&
      !modal.open &&
      !this.transitioning &&
      (Phaser.Input.Keyboard.JustDown(this.keyE) ||
        (this.autoNPC && !this.player.target))
    ) {
      this.autoNPC = false;
      this.player.body.stop();
      dialogue(this.keeper);
    }
  }
}
