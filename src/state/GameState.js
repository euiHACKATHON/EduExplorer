import { getLevel, levels } from "../config.js";

const key = "mars-colony-v1";
const blank = () => ({ xp: 0, completed: [], mastery: {}, mistakes: [], chapterProgress: {} });
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
    if (!Array.isArray(this.data.mistakes)) this.data.mistakes = [];
    if (!Number.isFinite(this.data.xp)) this.data.xp = 0;
    if (!this.data.chapterProgress || typeof this.data.chapterProgress !== "object") this.data.chapterProgress = {};
  }
  snapshot() {
    return {
      xp: this.data.xp,
      completed: [...(this.data.completed || [])],
      mastery: { ...this.data.mastery },
      mistakes: [...(this.data.mistakes || [])],
      chapterProgress: { ...(this.data.chapterProgress || {}) },
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
    Object.assign(this.data, blank(), progress || this.profiles[mode] || {});
    if (!Array.isArray(this.data.mistakes)) this.data.mistakes = [];
    this.save();
  }
  isMissionUnlocked(mission) {
    const level = getLevel(mission);
    if (level < 0) return false;
    return levels
      .slice(0, level)
      .every((earlier) => this.data.completed.includes(earlier.mission));
  }
  award(mission, result) {
    if (!this.isMissionUnlocked(mission)) return false;
    if (result.correct && !this.data.completed.includes(mission)) {
      this.data.completed.push(mission);
      this.data.xp += result.xp_earned;
    }
    this.data.mastery[mission] = Math.max(
      this.data.mastery[mission] || 0,
      result.mastery,
    );
    this.save();
    return result.correct;
  }
  answerChapterQuestion(chapter, questionId, correct, hints = 0) {
    const progress = new Set(this.data.chapterProgress[chapter] || []);
    if (correct) progress.add(questionId);
    this.data.chapterProgress[chapter] = [...progress];
    const complete = progress.size >= 10;
    const wasComplete = this.data.completed.includes(chapter);
    if (complete && !wasComplete) {
      this.data.completed.push(chapter);
      this.data.xp += Math.max(250, 500 - hints * 15);
    }
    this.data.mastery[chapter] = Math.round((progress.size / 10) * 100) / 100;
    this.save();
    return { complete, wasComplete, answered: progress.size };
  }
  recordMistake(question, selected, feedback = "") {
    const option = question.options.find((item) => item.id === selected);
    const existing = this.data.mistakes.find(
      (item) => item.questionId === question.question_id && !item.resolved,
    );
    if (existing) {
      existing.attempts += 1;
      existing.lastTried = Date.now();
      existing.feedback = feedback || existing.feedback;
    } else {
      this.data.mistakes.unshift({
        mission: question.mission_id,
        questionId: question.question_id,
        title: question.title,
        subject: question.subject,
        question: question.question,
        answerId: selected,
        answerText: option?.text || selected,
        feedback,
        attempts: 1,
        lastTried: Date.now(),
        resolved: false,
      });
    }
    this.save();
  }
  resolveMistakes(questionId) {
    let changed = false;
    this.data.mistakes.forEach((item) => {
      if (item.questionId === questionId && !item.resolved) {
        item.resolved = true;
        changed = true;
      }
    });
    if (changed) this.save();
  }
  sync(progress) {
    Object.assign(this.data, progress);
    this.save();
  }
}
export const state = new GameState();
