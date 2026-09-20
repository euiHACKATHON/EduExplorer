import test from "node:test";
import assert from "node:assert/strict";
import { ProceduralAudio } from "../src/audio/AudioManager.js";
import { smoothVelocity } from "../src/entities/movement.js";

function audioDevice(state = "running") {
  const nodes = [];
  const parameter = () => ({
    value: 0,
    setValueAtTime(v) {
      this.value = v;
    },
    linearRampToValueAtTime() {},
    exponentialRampToValueAtTime() {},
    setTargetAtTime(v) {
      this.value = v;
    },
    cancelScheduledValues() {},
  });
  const node = () => {
    const item = {
      gain: parameter(),
      frequency: parameter(),
      connect() {},
      disconnect() {
        this.disconnected = true;
      },
      start() {},
      stop() {
        this.stopped = true;
        this.onended?.();
      },
    };
    nodes.push(item);
    return item;
  };
  const context = {
    state,
    currentTime: 0,
    destination: {},
    createGain: node,
    createOscillator: node,
    sampleRate: 8000,
    createBuffer: (_channels, length) => ({
      getChannelData: () => new Float32Array(length),
    }),
    createBufferSource: node,
    createBiquadFilter: node,
    async resume() {
      this.state = "running";
    },
  };
  return { context, nodes };
}

test("audio safely supports absent devices and pre-gesture playback", () => {
  const audio = new ProceduralAudio();
  audio.init({ sound: {} });
  audio.playAmbient(0);
  audio.footstep();
  audio.blip();
  audio.chime();
  audio.travelWhoosh();
  audio.celebrate();
  audio.setMuted(true);
  audio.stopAmbient();
  audio.destroy();
  const device = audioDevice("suspended");
  audio.init({ sound: device });
  audio.playAmbient(1);
  audio.chime();
  assert.equal(audio.ambient, null);
  assert.equal(device.nodes.length, 1);
  audio.destroy();
});

test("ambience starts after gesture, stays singular, and stops on scene exit", async () => {
  const audio = new ProceduralAudio();
  const device = audioDevice("suspended");
  audio.init({ sound: device });
  audio.playAmbient(0);
  audio.unlock();
  await Promise.resolve();
  const first = audio.ambient;
  assert.equal(first.voices.length, 3);
  audio.playAmbient(0);
  assert.equal(audio.ambient, first);
  audio.playAmbient(2);
  assert.ok(first.voices.every((v) => v.stopped && v.disconnected));
  const second = audio.ambient;
  audio.stopAmbient();
  assert.equal(audio.realm, null);
  assert.ok(second.voices.every((v) => v.stopped));
  audio.destroy();
});

test("mute suppresses effects and destroy disconnects audio", () => {
  const audio = new ProceduralAudio();
  const device = audioDevice();
  audio.init({ sound: device });
  audio.setMuted(true);
  const count = device.nodes.length;
  audio.chime();
  audio.footstep();
  audio.travelWhoosh();
  assert.equal(device.nodes.length, count);
  assert.equal(audio.master.gain.value, 0);
  audio.destroy();
  assert.ok(audio.master.disconnected);
});

test("movement smoothing is frame-rate independent and brakes promptly", () => {
  const simulate = (fps) => {
    let velocity = 0;
    for (let i = 0; i < fps; i++)
      velocity = smoothVelocity(velocity, 180, 1000 / fps);
    return velocity;
  };
  assert.ok(Math.abs(simulate(30) - simulate(120)) < 0.001);
  assert.ok(smoothVelocity(0, 180, 16.67) > 0);
  assert.ok(smoothVelocity(0, 180, 16.67) < 180);
  let velocity = 180;
  for (let i = 0; i < 20; i++)
    velocity = smoothVelocity(velocity, 0, 1000 / 60, true);
  assert.equal(velocity, 0);
});

test("new interaction and environmental cues produce audio and obey mute", () => {
  const audio = new ProceduralAudio();
  const device = audioDevice();
  audio.init({ sound: device });
  audio.setMuted(false);
  const cues = [
    "click",
    "select",
    "correct",
    "incorrect",
    "hint",
    "landing",
    "arrival",
    "dustGust",
  ];
  for (const cue of cues) {
    const before = device.nodes.length;
    audio[cue]();
    assert.ok(device.nodes.length > before, `${cue} produces audio`);
    assert.ok(
      device.nodes.slice(before).every((n) => n.disconnected),
      `${cue} cleans up`,
    );
  }
  audio.setMuted(true);
  const before = device.nodes.length;
  cues.forEach((cue) => audio[cue]());
  assert.equal(device.nodes.length, before);
  audio.destroy();
});

test("fresh effects survive a pending audio resume without replaying muted cues", async () => {
  const audio = new ProceduralAudio();
  const device = audioDevice("suspended");
  let resume;
  device.context.resume = () =>
    new Promise((resolve) => {
      resume = () => {
        device.context.state = "running";
        resolve();
      };
    });
  audio.init({ sound: device });
  const ready = audio.unlock();
  audio.select();
  assert.equal(device.nodes.length, 1);
  resume();
  await ready;
  assert.equal(device.nodes.length, 3);
  device.context.state = "suspended";
  const next = audio.unlock();
  audio.correct();
  audio.setMuted(true);
  resume();
  await next;
  assert.equal(device.nodes.length, 3);
  audio.destroy();
});

test("delegated clicks skip disabled buttons and controls with specific cues", () => {
  const audio = new ProceduralAudio();
  audio.init({ sound: audioDevice() });
  let clicks = 0;
  audio.click = () => clicks++;
  const button = { disabled: false, dataset: {}, getAttribute: () => null };
  const event = { target: { closest: () => button } };
  audio.onClick(event);
  assert.equal(clicks, 1);
  button.dataset.sound = "custom";
  audio.onClick(event);
  delete button.dataset.sound;
  button.disabled = true;
  audio.onClick(event);
  assert.equal(clicks, 1);
  audio.destroy();
});
