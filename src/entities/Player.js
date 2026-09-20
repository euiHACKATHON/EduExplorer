import Phaser from "phaser";
import { AudioManager } from "../audio/AudioManager.js";
import { smoothVelocity } from "./movement.js";
export class Player extends Phaser.Physics.Arcade.Sprite {
  constructor(scene, x, y, texture) {
    super(scene, x, y, texture);
    scene.add.existing(this);
    scene.physics.add.existing(this);
    this.setCollideWorldBounds(true);
    this.body.setSize(22, 20).setOffset(9, 28);
    this.speed = 180;
    this.cursors = scene.input.keyboard.createCursorKeys();
    this.wasd = scene.input.keyboard.addKeys("W,A,S,D");
    // Keep gameplay keys readable by Phaser without preventing those same
    // characters (or spaces) from being entered in lesson chat fields.
    scene.input.keyboard.removeCapture([
      Phaser.Input.Keyboard.KeyCodes.W,
      Phaser.Input.Keyboard.KeyCodes.A,
      Phaser.Input.Keyboard.KeyCodes.S,
      Phaser.Input.Keyboard.KeyCodes.D,
      Phaser.Input.Keyboard.KeyCodes.SPACE,
    ]);
    this.target = null;
    this.stepDistance = 0;
    this.lastPosition = { x, y };
    this.walkPhase = 0;
  }
  update(blocked, delta = 16.67) {
    const traveled = Phaser.Math.Distance.BetweenPoints(
      this,
      this.lastPosition,
    );
    this.lastPosition = { x: this.x, y: this.y };
    if (blocked) {
      this.body.stop();
      this.setScale(1);
      this.stepDistance = 0;
      return;
    }
    let x =
        Number(this.cursors.right.isDown || this.wasd.D.isDown) -
        Number(this.cursors.left.isDown || this.wasd.A.isDown),
      y =
        Number(this.cursors.down.isDown || this.wasd.S.isDown) -
        Number(this.cursors.up.isDown || this.wasd.W.isDown);
    if (x || y) this.target = null;
    else if (this.target) {
      const dist = Phaser.Math.Distance.Between(
        this.x,
        this.y,
        this.target.x,
        this.target.y,
      );
      if (dist > 5) {
        x = this.target.x - this.x;
        y = this.target.y - this.y;
      } else {
        this.target = null;
        this.body.stop();
      }
    }
    const direction = new Phaser.Math.Vector2(x, y).normalize();
    // Slow near click destinations to prevent overshoot with acceleration.
    const speed = this.target
      ? Math.min(this.speed, Math.hypot(x, y) * 9)
      : this.speed;
    this.body.setVelocity(
      smoothVelocity(
        this.body.velocity.x,
        direction.x * speed,
        delta,
        !x && !y,
      ),
      smoothVelocity(
        this.body.velocity.y,
        direction.y * speed,
        delta,
        !x && !y,
      ),
    );
    if (traveled > 0.1 && traveled < 30) {
      this.stepDistance += traveled;
      this.walkPhase += traveled * 0.22;
      const stride = Math.sin(this.walkPhase) * 0.035;
      this.setScale(1 + stride, 1 - stride);
      if (this.stepDistance >= 25) {
        this.stepDistance %= 25;
        AudioManager.footstep();
        const dust = this.scene.add
          .circle(this.x, this.y + 22, 3, this.scene.level.accent, 0.24)
          .setDepth(this.depth - 1);
        this.scene.tweens.add({
          targets: dust,
          y: dust.y - 8,
          x: dust.x + Phaser.Math.Between(-6, 6),
          alpha: 0,
          scale: 2,
          duration: 350,
          onComplete: () => dust.destroy(),
        });
      }
    } else this.setScale(1);
    if (x) this.setFlipX(x < 0);
    this.setDepth(Math.max(10, this.y));
  }
}
