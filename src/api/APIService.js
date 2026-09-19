import { state } from "../state/GameState.js";

const TOKEN_KEY = "mars-colony-token";

export class APIService {
  constructor(
    baseUrl = import.meta.env?.VITE_API_URL || "/api",
    useMock = true,
  ) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.useMock = useMock;
    let savedToken = null;
    try {
      savedToken = globalThis.localStorage?.getItem(TOKEN_KEY) || null;
    } catch {}
    this.token = savedToken;
  }
  setToken(token) {
    this.token = token;
    try {
      globalThis.localStorage?.setItem(TOKEN_KEY, token);
    } catch {}
  }
  clearToken() {
    this.token = null;
    try {
      globalThis.localStorage?.removeItem(TOKEN_KEY);
    } catch {}
  }
  // `authed` defaults to true for any call against our own backend (the
  // /auth/* routes ignore the header anyway); pass authed:false only for
  // requests -- like the /mock/*.json files -- that must never carry it.
  async request(path, payload, { authed = true } = {}) {
    let res;
    const headers = {};
    if (payload) headers["Content-Type"] = "application/json";
    if (authed && this.token) headers["Authorization"] = `Bearer ${this.token}`;
    try {
      res = await fetch(path, {
        ...(payload ? { method: "POST", body: JSON.stringify(payload) } : {}),
        headers,
        signal: AbortSignal.timeout(25000),
      });
    } catch {
      throw new Error(
        "Connection unavailable. Check the backend or switch to offline mode in Settings.",
      );
    }
    if (res.status === 401) {
      // Stale/expired token -- drop it so the next "Connect to Live AI"
      // attempt shows the sign-in form again instead of failing silently.
      this.clearToken();
      throw new Error("Your session expired. Please sign in again.");
    }
    if (!res.ok) {
      let detail = "";
      try {
        const body = await res.json();
        if (typeof body?.detail === "string") detail = body.detail;
        else if (Array.isArray(body?.detail))
          // FastAPI validation errors (422): a list of {msg, loc, ...}.
          detail = body.detail.map((d) => d.msg || JSON.stringify(d)).join("; ");
      } catch {}
      throw new Error(
        detail ||
          `Request failed (${res.status}). Please try again or use offline mode.`,
      );
    }
    return res.json();
  }
  async register({ student_id, display_name, grade_level, password }) {
    const data = await this.request(
      `${this.baseUrl}/auth/register`,
      { student_id, display_name, grade_level: grade_level || null, password },
      { authed: false },
    );
    this.setToken(data.access_token);
    return data;
  }
  async login({ student_id, password }) {
    const data = await this.request(
      `${this.baseUrl}/auth/login`,
      { student_id, password },
      { authed: false },
    );
    this.setToken(data.access_token);
    return data;
  }
  async getNPCDialogue(id) {
    return this.useMock
      ? this.request(`/mock/dialogue_${id}.json`, undefined, { authed: false })
      : this.request(
          `${this.baseUrl}/ai/dialogue?npc_id=${encodeURIComponent(id)}&student_id=${encodeURIComponent(state.data.student_id)}`,
        );
  }
  async getChallenge(id) {
    return this.useMock
      ? this.request(`/mock/challenge_${id}.json`, undefined, { authed: false })
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
  async askTutor(missionId, message) {
    if (this.useMock)
      throw new Error("Connect to Live AI before opening the tutor channel.");
    return this.request(`${this.baseUrl}/ai/ask`, {
      mission_id: missionId,
      student_id: state.data.student_id,
      message,
    });
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