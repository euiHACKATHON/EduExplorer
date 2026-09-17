import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { APIService } from "../src/api/APIService.js";
import { state, GameState } from "../src/state/GameState.js";
const originalFetch = globalThis.fetch;
globalThis.fetch = async (path) => ({
  ok: true,
  json: async () => JSON.parse(await readFile(`public${path}`, "utf8")),
});
test("offline assessments reject wrong answers, award hints-adjusted XP, and prevent repeat rewards", async () => {
  const api = new APIService("/api", true);
  state.data.completed = [];
  const p = {
    mission_id: "M001",
    question_id: "Q001",
    answer: "A",
    hints_used: 0,
  };
  assert.equal((await api.submitAssessment(p)).correct, false);
  p.answer = "C";
  p.hints_used = 2;
  const result = await api.submitAssessment(p);
  assert.equal(result.xp_earned, 70);
  state.award("M001", result);
  assert.equal((await api.submitAssessment(p)).xp_earned, 0);
  await assert.rejects(() =>
    api.submitAssessment({ ...p, question_id: "bad" }),
  );
});
test("all missions have consistent choices and three scaffolded hints", async () => {
  const api = new APIService("/api", true);
  for (const id of ["M001", "M002", "M003"]) {
    const q = await api.getChallenge(id);
    assert.equal(q.options.filter((o) => o.id === q.answer).length, 1);
    assert.equal(q.hints.length, 3);
    assert.equal(
      (await api.requestHint({ mission_id: id, level: 2 })).hint,
      q.hints[1],
    );
  }
});
test("save/load survives corrupt and unavailable storage", () => {
  const fake = {
    getItem: () => "{bad",
    setItem: () => {
      throw Error("full");
    },
  };
  const game = new GameState(fake);
  assert.equal(game.data.xp, 0);
  assert.doesNotThrow(() => game.save());
});
test("live assessments send the expected JSON POST", async () => {
  let seen;
  globalThis.fetch = async (url, options) => {
    seen = { url, options };
    return { ok: true, json: async () => ({ correct: true }) };
  };
  const api = new APIService("/api", false);
  await api.submitAssessment({ answer: "C" });
  assert.equal(seen.url, "/api/assessment");
  assert.equal(seen.options.method, "POST");
  assert.deepEqual(JSON.parse(seen.options.body), { answer: "C" });
  globalThis.fetch = originalFetch;
});

test("offline and live progress remain separate across mode switches and reload", () => {
  let saved;
  const memory = {
    getItem: () => saved,
    setItem: (_, value) => (saved = value),
  };
  const game = new GameState(memory);
  game.award("M001", { correct: true, xp_earned: 100, mastery: 1 });
  game.setMode("live", {
    xp: 85,
    completed: ["M002"],
    mastery: { M002: 0.85 },
  });
  assert.equal(game.data.xp, 85);
  const reloaded = new GameState(memory);
  assert.equal(reloaded.data.xp, 100);
  assert.deepEqual(reloaded.data.completed, ["M001"]);
  game.setMode("offline");
  assert.equal(game.data.xp, 100);
});
