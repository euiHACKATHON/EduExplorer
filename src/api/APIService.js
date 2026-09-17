import { state } from "../state/GameState.js";
export class APIService {
  constructor(
    baseUrl = import.meta.env?.VITE_API_URL || "/api",
    useMock = true,
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.useMock = useMock;
  }
  async request(path, payload) {
    let res;
    try {
      res = await fetch(path, {
        ...(payload
          ? {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify(payload),
            }
          : {}),
        signal: AbortSignal.timeout(25000),
      });
    } catch {
      throw new Error(
        "Connection unavailable. Check the backend or switch to offline mode in Settings.",
      );
    }
    if (!res.ok)
      throw new Error(
        `Request failed (${res.status}). Please try again or use offline mode.`,
      );
    return res.json();
  }
  async getNPCDialogue(id) {
    return this.useMock
      ? this.request(`/mock/dialogue_${id}.json`)
      : this.request(
          `${this.baseUrl}/ai/dialogue?npc_id=${encodeURIComponent(id)}&student_id=${encodeURIComponent(state.data.student_id)}`,
        );
  }
  async getChallenge(id) {
    return this.useMock
      ? this.request(`/mock/challenge_${id}.json`)
      : this.request(`${this.baseUrl}/challenges/${id}`);
  }
  async submitAssessment(payload) {
    if (!this.useMock)
      return this.request(`${this.baseUrl}/assessment`, payload);
    const q = await this.getChallenge(payload.mission_id);
    if (
      q.question_id !== payload.question_id ||
      !q.options.some((o) => o.id === payload.answer)
    )
      throw new Error("Invalid answer. Please reopen the mission.");
    const correct = payload.answer === q.answer;
    return {
      correct,
      xp_earned:
        correct && !state.data.completed.includes(q.mission_id)
          ? Math.max(50, 100 - payload.hints_used * 15)
          : 0,
      mastery: correct
        ? Math.max(0.6, 1 - payload.hints_used * 0.15)
        : state.data.mastery[q.mission_id] || 0.2,
      feedback: correct
        ? q.explanation
        : "Not quite. Check the relationship between the quantities, then try again.",
      source: "offline",
    };
  }
  async requestHint(payload) {
    if (!this.useMock) return this.request(`${this.baseUrl}/ai/hint`, payload);
    const q = await this.getChallenge(payload.mission_id);
    return {
      hint: q.hints[Math.min(payload.level - 1, q.hints.length - 1)],
      source: "offline",
    };
  }
  async explain(id) {
    if (!this.useMock)
      return this.request(`${this.baseUrl}/ai/explain`, { mission_id: id });
    const q = await this.getChallenge(id);
    return { message: q.lesson, source: "offline" };
  }
  async getProgress() {
    return this.useMock
      ? state.data
      : this.request(
          `${this.baseUrl}/students/${encodeURIComponent(state.data.student_id)}/progress`,
        );
  }
}
export const api = new APIService();
