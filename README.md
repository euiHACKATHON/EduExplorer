# EduExplorer — Mars Colony Explorer

A playable Phaser 3 science adventure based on the supplied implementation plan. Explore Arcadia Base, choose a suit, speak with three crewmates, solve science missions, request hints, and restore the colony.

## Run the game

Requires Node.js 20.19+ (or 22.12+).

```sh
npm install
npm run dev
```

Open http://127.0.0.1:5173. The game starts in offline mode and needs no API key. Move with WASD/arrows and press E near a crewmate. Click a crewmate or a mission-log entry to walk there automatically. Clicking terrain also moves the explorer. Escape closes dialogs.

## Enable generative AI

Requires Python 3.10+.

```sh
python -m venv .venv
# Windows:
.venv/Scripts/python -m pip install -r backend/requirements.txt
# macOS/Linux: use .venv/bin/python instead
```

Copy `.env.example` to `.env`. Set `OPENAI_API_KEY` there and, optionally, `OPENAI_MODEL` to a Responses-compatible model your account can access. Never put an API key in a `VITE_` variable or browser code.

```sh
.venv/Scripts/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Keep Vite running in another terminal. Choose **Settings → Connect to live AI**. The Vite `/api` proxy forwards requests to FastAPI. API documentation: http://127.0.0.1:8000/docs.

The integration uses the [OpenAI Responses API](https://developers.openai.com/api/docs/guides/text). It generates NPC mission briefings, concept explanations, and progressively scaffolded hints from reviewed lesson facts. No names or student IDs are sent to OpenAI. Generated text is inserted as text, never HTML. If generation fails, the game labels and uses authored fallback content.

The three multiple-choice questions and their answer keys are deliberately authored; grading is deterministic, not performed by the language model. The current mastery score is a simple learning indicator based on correct answers and hints, not a calibrated Item Response Theory model. Generated content may need educator review.

## Included missions

- **Unstick the rover:** Newton's second law and net force.
- **Power the outpost:** Power, time, and energy in watt-hours.
- **Grow a greener Mars:** Inputs and outputs of photosynthesis.

Each first successful mission earns 100 XP minus 15 per hint, with up to three hints. Retries are allowed; repeated success does not farm XP. Progress and suit choice are saved locally. Live progress is saved in SQLite; offline and live scores are separate.

## Structure

`src/scenes/` contains Boot, MainMenu, CharacterSelect, and MarsColony scenes. `src/entities/` contains the player controller and NPCs. `src/ui/` contains accessible HTML dialogs and the mission dashboard. `src/api/APIService.js` owns mock/live HTTP operations. `public/mock/` contains lesson JSON; Vite serves these at `/mock/`, not `/public/mock/`. `backend/main.py` provides dialogue, hints, explanations, challenges, assessment, and student-progress endpoints. Colony art is generated in Phaser; no external art files are required.

## Validation

```sh
npm test
npm run build
.venv/Scripts/python -m pytest backend/test_api.py -q
```

Tests cover right/wrong answers, question validation, hint data, duplicate XP prevention, persistence, mode isolation, request payloads, private server answer keys, and AI fallback behavior. Browser checks cover welcome/suit selection, NPC navigation, dialogue, challenges, retries, hints, and completion feedback.

`npm run build` outputs `dist/`. For production hosting, serve that directory and route `/api` to FastAPI, or set `VITE_API_URL` before building and configure the backend's allowed origins. Vite's development proxy is not a production server.

This is a local playable prototype. Public classroom deployment needs authentication, server-enforced learner identity, per-user request/rate limits, and educator review. Client-reported timing/hint counts are advisory; they are not suitable for high-stakes grading. The backend does not currently implement IRT or an educator dashboard.

## Verification record

- Frontend: 5 automated tests passed.
- Backend: 4 automated tests passed, including simulated OpenAI responses and provider timeouts.
- Production build passed.
- Browser: character selection, walking to NPC, explanations, wrong answers, hint retrieval, correct completion, and XP checked.
- No OpenAI key was configured during implementation; a real provider request has not been run.

## Clone EduExplorer

After cloning the repository, run all commands from its root directory:

```sh
git clone https://github.com/jalasamir21/EduExplorer.git
cd EduExplorer
npm ci
npm run dev
```

For a private repository, sign in to GitHub with an account that has access before cloning.

## Complete platform-specific setup

### Windows PowerShell

First terminal (frontend):

```powershell
npm ci
npm run dev
```

Second terminal (optional AI backend):

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
Copy-Item .env.example .env
# Edit .env and set OPENAI_API_KEY before starting the backend.
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Copy the example only during first setup; do not overwrite an existing `.env`. Using the virtual environment's Python directly avoids PowerShell activation-policy issues.

### macOS / Linux

First terminal:

```sh
npm ci
npm run dev
```

Second terminal:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt
cp .env.example .env
# Edit .env and set OPENAI_API_KEY.
.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Then open http://127.0.0.1:5173 and select **Settings → Connect to live AI**. Keep both terminals running. Stop each process with Ctrl+C. Without the backend, offline gameplay still works.

## Configuration reference

| Variable | Location | Purpose |
| --- | --- | --- |
| `OPENAI_API_KEY` | Server `.env` | Enables generated dialogue, explanations, and hints. |
| `OPENAI_MODEL` | Server `.env` | Responses model; default `gpt-4.1-mini`. Requires account access. |
| `VITE_API_URL` | Frontend build environment | API base URL; default `/api`. Never use for secrets. |
| `MARS_DB` | Server environment | Optional SQLite file path; default `backend/progress.sqlite3`. |

`package-lock.json` records frontend dependencies; use `npm ci` for repeatable installs. `backend/requirements-lock.txt` records the Python environment used for validation on Windows/Python 3.12. `backend/requirements.txt` lists supported dependency ranges for portable setup.

## API and data flow

1. The player approaches a crewmate and opens a dialogue.
2. `APIService` reads local JSON in offline mode or calls FastAPI in live mode.
3. The learner opens the associated challenge and chooses an answer.
4. Hints are authored offline or generated on the server using the lesson facts.
5. The assessment service checks the selected answer against the authored key and awards XP once.
6. The dashboard updates completion and mastery. Live results persist in SQLite; local results persist in browser storage.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Backend status and whether a key is configured; does not validate the key. |
| GET | `/ai/dialogue?npc_id=scientist_01` | Crewmate briefing and available actions. |
| GET | `/challenges/M001` | Mission question and answer choices. |
| POST | `/ai/hint` | Hint for a mission/question at level 1–3. |
| POST | `/ai/explain` | Explanation of a mission's science concept. |
| POST | `/assessment` | Deterministic grading, XP, mastery, and feedback. |
| GET | `/students/{student_id}/progress` | Saved server progress for the anonymous explorer ID. |

Request schemas and interactive examples are available at the running backend's `/docs` page. Live challenge responses omit answer keys, but the bundled offline JSON intentionally contains them: this is a learning game, not a secure examination platform.

## Controls and restarting

- WASD or arrow keys: move.
- E near a crewmate: interact.
- Click a crewmate or mission: walk there automatically.
- Click the map: walk to that point.
- Escape or the close button: close the current dialog.
- **Settings → Restart offline expedition:** explicitly reset local XP, completion, and mastery after confirmation. Server progress is unchanged.

## Troubleshooting

| Symptom | What to do |
| --- | --- |
| `npm` is not recognized | Install Node.js and reopen the terminal. |
| `py` or `python3` is not recognized | Install Python, then reopen the terminal. |
| Blank page from opening `index.html` | Run Vite and use the local URL; do not open the file directly. |
| Live AI says connection unavailable | Start FastAPI on port 8000 and keep the backend terminal open. |
| Live AI says no key is configured | Set the server's `OPENAI_API_KEY` in `.env` and restart FastAPI. |
| Authored fallback appears in live mode | Check the API key, account access, model name, quota, and network connectivity. |
| Port 5173 is occupied | Use Vite's displayed URL. The same-origin `/api` development proxy still forwards to port 8000. |
| Progress seems different between modes | Offline and live progress are deliberately stored separately. |

## Extending the project

Edit `public/mock/challenge_M001.json` and the other lesson JSON files to change questions, hints, and explanations. `seed.mjs` regenerates the original JSON, so update the seed too if you intend to regenerate data. To add a fourth mission, also extend `src/config.js`, dashboard rendering, and the backend mission/NPC allowlists and validation models; the current game has three fixed mission slots.

The original project brief is preserved in `output_PhaserJS_Educational_Game_Implementation_Plan.md`. This README describes the implemented behavior and its current limitations.

