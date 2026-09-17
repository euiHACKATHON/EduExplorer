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
    scene.add
      .circle(data.x, data.y - 40, 10, 0xf5c880)
      .setStrokeStyle(2, 0x6b4735);
    scene.add
      .text(data.x, data.y - 40, "!", {
        fontSize: 15,
        color: "#563b27",
        fontStyle: "bold",
      })
      .setOrigin(0.5);
  }
}
