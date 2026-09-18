import Phaser from "phaser";
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
  }
  update(blocked) {
    this.body.setVelocity(0);
    if (blocked) return;
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
      } else this.target = null;
    }
    this.body.setVelocity(x, y);
    this.body.velocity.normalize().scale(this.speed);
    if (x) this.setFlipX(x < 0);
    this.setDepth(this.y);
  }
}
