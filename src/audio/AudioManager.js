// Procedural audio uses Phaser's context, so no downloads or second audio engine
// are needed. A missing/blocked audio device must never prevent play.
export class ProceduralAudio {
  constructor() {
    this.muted = false;
    this.realm = null;
    this.ambient = null;
  }

  init(scene) {
    if (this.context) return;
    const context = scene?.sound?.context;
    if (!context?.createGain) return;
    this.context = context;
    this.master = context.createGain();
    this.master.connect(scene.sound.masterMuteNode || context.destination);
    try {
      this.muted =
        globalThis.localStorage?.getItem("edu-audio-muted") === "true";
    } catch {}
    this.master.gain.value = this.muted ? 0 : 0.55;
    this.unlock = () => {
      if (context.state === "closed") return;
      if (this.resumePromise) return this.resumePromise;
      try {
        this.resumePromise = Promise.resolve(context.resume())
          .then(() => {
            if (this.context === context) this.startAmbient();
          })
          .catch(() => {})
          .finally(() => {
            this.resumePromise = null;
          });
        return this.resumePromise;
      } catch {
        /* Audio can be unavailable even after a user gesture. */
      }
    };
    globalThis.document?.addEventListener("pointerdown", this.unlock);
    globalThis.document?.addEventListener("keydown", this.unlock);
    // Capture before handlers replace dialogs or disable the clicked button.
    // Native click also covers keyboard activation without duplicate key sounds.
    this.onClick = (event) => {
      const button = event.target?.closest?.("button");
      if (
        !button ||
        button.disabled ||
        button.getAttribute("aria-disabled") === "true" ||
        button.dataset.sound === "custom"
      )
        return;
      this.unlock();
      this.click();
    };
    globalThis.document?.addEventListener("click", this.onClick, true);
    this.visibility = () => {
      this.master.gain.setTargetAtTime(
        this.muted || document.hidden ? 0 : 0.55,
        context.currentTime,
        0.05,
      );
    };
    globalThis.document?.addEventListener("visibilitychange", this.visibility);
    scene.game?.events.once("destroy", () => this.destroy());
  }

  setMuted(value) {
    this.muted = Boolean(value);
    try {
      globalThis.localStorage?.setItem("edu-audio-muted", String(this.muted));
    } catch {}
    if (this.context) {
      this.master.gain.setTargetAtTime(
        this.muted ? 0 : 0.55,
        this.context.currentTime,
        0.04,
      );
      if (!this.muted) this.unlock();
    }
  }

  tone(
    frequency,
    duration,
    volume = 0.1,
    delay = 0,
    endFrequency = frequency,
    type = "sine",
  ) {
    const ctx = this.context;
    if (!ctx || this.muted || globalThis.document?.hidden) return;
    if (ctx.state !== "running") {
      // Replay only a fresh cue while a user-initiated resume is in flight.
      // Never accumulate old footsteps or weather for a later interaction.
      if (this.resumePromise && (this.waitingTones || 0) < 8) {
        const requested = Date.now();
        this.waitingTones = (this.waitingTones || 0) + 1;
        this.resumePromise.then(() => {
          this.waitingTones--;
          if (
            this.context === ctx &&
            ctx.state === "running" &&
            Date.now() - requested < 350
          )
            this.tone(frequency, duration, volume, delay, endFrequency, type);
        });
      }
      return;
    }
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    const start = ctx.currentTime + delay;
    oscillator.type = type;
    oscillator.frequency.setValueAtTime(frequency, start);
    oscillator.frequency.exponentialRampToValueAtTime(
      endFrequency,
      start + duration,
    );
    gain.gain.setValueAtTime(0, start);
    gain.gain.linearRampToValueAtTime(
      volume,
      start + Math.min(0.04, duration / 4),
    );
    gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
    oscillator.connect(gain);
    gain.connect(this.master);
    oscillator.onended = () => {
      oscillator.disconnect();
      gain.disconnect();
    };
    oscillator.start(start);
    oscillator.stop(start + duration + 0.02);
  }

  footstep() {
    this.tone(100 + Math.random() * 35, 0.075, 0.085, 0, 45, "triangle");
  }
  blip() {
    this.tone(660, 0.14, 0.07, 0, 880);
  }
  click() {
    this.tone(520, 0.065, 0.09, 0, 700);
  }
  select() {
    this.tone(780, 0.11, 0.12, 0, 980);
  }
  correct() {
    [659, 831, 1046].forEach((f, i) => this.tone(f, 0.36, 0.13, i * 0.09));
  }
  incorrect() {
    this.tone(330, 0.2, 0.12, 0, 247, "triangle");
    this.tone(247, 0.2, 0.09, 0.15, 220, "triangle");
  }
  hint() {
    this.tone(587, 0.22, 0.1);
    this.tone(880, 0.32, 0.09, 0.12);
  }
  landing(step = 0) {
    this.tone(120, 0.16, 0.16, 0, 55, "triangle");
    this.tone(523 * 2 ** (step / 12), 0.24, 0.09, 0.025);
  }
  arrival() {
    [262, 392, 523, 784].forEach((f, i) => this.tone(f, 0.85, 0.11, i * 0.13));
  }
  dustGust() {
    const ctx = this.context;
    if (
      !ctx ||
      ctx.state !== "running" ||
      this.muted ||
      globalThis.document?.hidden
    )
      return;
    const duration = 2.4;
    const buffer = ctx.createBuffer(
      1,
      Math.ceil(ctx.sampleRate * duration),
      ctx.sampleRate,
    );
    const samples = buffer.getChannelData(0);
    for (let i = 0; i < samples.length; i++) samples[i] = Math.random() * 2 - 1;
    const source = ctx.createBufferSource();
    const filter = ctx.createBiquadFilter();
    const gain = ctx.createGain();
    const now = ctx.currentTime;
    source.buffer = buffer;
    filter.type = "lowpass";
    filter.frequency.setValueAtTime(500, now);
    filter.frequency.linearRampToValueAtTime(1400, now + 0.9);
    filter.frequency.linearRampToValueAtTime(350, now + duration);
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.2, now + 0.8);
    gain.gain.linearRampToValueAtTime(0, now + duration);
    source.connect(filter);
    filter.connect(gain);
    gain.connect(this.master);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      gain.disconnect();
    };
    source.start(now);
    source.stop(now + duration);
  }
  chime() {
    [523, 659, 784].forEach((f, i) => this.tone(f, 0.5, 0.065, i * 0.09));
  }
  travelWhoosh(duration = 2.95) {
    this.tone(70, duration, 0.14, 0, 700, "triangle");
    this.tone(140, duration, 0.07, 0, 1050);
  }

  playAmbient(realmIndex) {
    if (this.realm === realmIndex && this.ambient) return;
    this.stopAmbient();
    this.realm = realmIndex;
    this.startAmbient();
  }

  startAmbient() {
    const ctx = this.context;
    if (!ctx || ctx.state !== "running" || this.realm === null || this.ambient)
      return;
    const gain = ctx.createGain();
    const now = ctx.currentTime;
    gain.gain.setValueAtTime(0, now);
    gain.gain.linearRampToValueAtTime(0.035, now + 1.4);
    gain.connect(this.master);
    const root = [73.42, 110, 130.81][this.realm] || 73.42;
    const voices = [1, 1.5, 2.002].map((ratio) => {
      const voice = ctx.createOscillator();
      voice.frequency.value = root * ratio;
      voice.connect(gain);
      voice.start();
      return voice;
    });
    this.ambient = { gain, voices };
  }

  celebrate() {
    this.chime();
    this.tone(1046, 1, 0.06, 0.3);
    if (!this.ambient) return;
    const now = this.context.currentTime;
    const gain = this.ambient.gain.gain;
    gain.cancelScheduledValues(now);
    gain.setValueAtTime(gain.value, now);
    gain.linearRampToValueAtTime(0.06, now + 0.4);
    gain.linearRampToValueAtTime(0.035, now + 1.8);
  }

  stopAmbient() {
    this.realm = null;
    if (!this.ambient) return;
    const { gain, voices } = this.ambient;
    const now = this.context.currentTime;
    gain.gain.cancelScheduledValues(now);
    gain.gain.setValueAtTime(gain.gain.value, now);
    gain.gain.linearRampToValueAtTime(0, now + 0.35);
    voices.forEach((voice, i) => {
      voice.onended = () => {
        voice.disconnect();
        if (i === voices.length - 1) gain.disconnect();
      };
      voice.stop(now + 0.4);
    });
    this.ambient = null;
  }

  destroy() {
    this.stopAmbient();
    globalThis.document?.removeEventListener("pointerdown", this.unlock);
    globalThis.document?.removeEventListener("keydown", this.unlock);
    globalThis.document?.removeEventListener("click", this.onClick, true);
    globalThis.document?.removeEventListener(
      "visibilitychange",
      this.visibility,
    );
    this.master?.disconnect();
    this.context = null;
  }
}

export const AudioManager = new ProceduralAudio();
