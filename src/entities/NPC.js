import Phaser from "phaser";
export class NPC extends Phaser.GameObjects.Sprite {
  constructor(scene, data, index) {
    super(scene, data.x, data.y, ["amber", "teal", "violet"][index]);
    scene.add.existing(this);
    this.info = data;
    this.setDepth(data.y).setInteractive({ useHandCursor: true });
    this.label = scene.add
      .text(data.x, data.y + 35, data.name, {
        fontFamily: "Arial",
        fontSize: 12,
        color: "#fff1dd",
        backgroundColor: "#49372fe0",
        padding: { x: 8, y: 5 },
      })
      .setOrigin(0.5)
      .setDepth(900);
    this.marker = scene.add.container(data.x, data.y - 40).setDepth(901);
    this.marker.add(
      scene.add.circle(0, 0, 10, 0xf5c880).setStrokeStyle(2, 0x6b4735),
    );
    this.marker.add(
      scene.add
        .text(0, 0, "!", {
          fontSize: 15,
          color: "#563b27",
          fontStyle: "bold",
        })
        .setOrigin(0.5),
    );
    scene.tweens.add({
      targets: this,
      y: data.y - 4,
      duration: 1400,
      yoyo: true,
      repeat: -1,
      ease: "Sine.easeInOut",
    });
    scene.tweens.add({
      targets: this.marker,
      scale: 1.15,
      duration: 950,
      yoyo: true,
      repeat: -1,
      ease: "Sine.easeInOut",
    });
  }
  facePlayer(playerX) {
    this.setFlipX(playerX < this.x);
  }
}
