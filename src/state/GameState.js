const key = "mars-colony-v1";
const blank = () => ({ xp: 0, completed: [], mastery: {} });
export class GameState {
  constructor(storage = globalThis.localStorage) {
    this.storage = storage;
    let saved;
    try {
      saved = JSON.parse(storage?.getItem(key) || "null");
    } catch {}
    this.data = {
      student_id: globalThis.crypto?.randomUUID?.() || "local-explorer",
      character: "amber",
      ...blank(),
      ...saved,
    };
    if (!Array.isArray(this.data.completed)) this.data.completed = [];
    this.mode = "offline";
    this.profiles = this.data.profiles || {
      offline: this.snapshot(),
      live: blank(),
    };
    Object.assign(this.data, this.profiles.offline);
    if (!Array.isArray(this.data.completed)) this.data.completed = [];
    if (!this.data.mastery || typeof this.data.mastery !== "object")
      this.data.mastery = {};
    if (!Number.isFinite(this.data.xp)) this.data.xp = 0;
  }
  snapshot() {
    return {
      xp: this.data.xp,
      completed: [...(this.data.completed || [])],
      mastery: { ...this.data.mastery },
    };
  }
  save() {
    this.profiles[this.mode] = this.snapshot();
    try {
      this.storage?.setItem(
        key,
        JSON.stringify({ ...this.data, profiles: this.profiles }),
      );
    } catch {}
  }
  setMode(mode, progress) {
    this.profiles[this.mode] = this.snapshot();
    this.mode = mode;
    Object.assign(this.data, progress || this.profiles[mode] || blank());
    this.save();
  }
  award(mission, result) {
    if (result.correct && !this.data.completed.includes(mission)) {
      this.data.completed.push(mission);
      this.data.xp += result.xp_earned;
    }
    this.data.mastery[mission] = Math.max(
      this.data.mastery[mission] || 0,
      result.mastery,
    );
    this.save();
  }
  sync(progress) {
    Object.assign(this.data, progress);
    this.save();
  }
}
export const state = new GameState();
