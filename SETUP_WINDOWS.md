# Setup on Windows + VS Code, everything installed globally (no virtual environment)

Run all commands from the project root: the folder that contains `package.json` and `backend`.

## 1. Tools (once)

```powershell
winget install Python.Python.3.12
winget install OpenJS.NodeJS.LTS
winget install Git.Git
```

Close and reopen VS Code, then check `python --version` (3.11 to 3.13 work), `node --version`
(20.19 or newer) and `git --version`. In VS Code install the **Python** extension, then
`Ctrl+Shift+P` → **Python: Select Interpreter** → pick that Python.

## 2. Python packages

```powershell
python -m pip install -r backend/requirements.txt
```

`pip install -r` keeps versions you already have and only adds what is missing. To preview first,
add `--dry-run`. Then optionally, for PDF uploads and semantic search (large: it installs PyTorch):

```powershell
python -m pip install -r backend/requirements-rag.txt
```

Person 3's module works without this second file.

## 3. Frontend packages (only to run the game in the browser)

```powershell
npm ci
```

## 4. Settings

```powershell
Copy-Item .env.example .env
```

Fill in `GROQ_API_KEY` (optional: without it the AI falls back to authored text) and set
`AUTH_SECRET` to any long random string. Add `RAG_ALLOW_UPLOAD=1` if you want to try uploads.

## 5. Check

```powershell
python -m backend.services.rag.check_install
python -m pytest test_api.py backend/tests -q
```

## 6. Run

```powershell
python -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000/docs and try `POST /rag/query`. For the game, run `npm run dev` in a
second terminal and open http://127.0.0.1:5173.

| Problem | Fix |
| --- | --- |
| `python` is not recognized | Reinstall Python with **Add python.exe to PATH**, or use `py`. |
| `No module named backend` | You are not in the project root. |
| Model download fails | Set `$env:RAG_EMBEDDER = "bm25"` to use keyword search. |
| pip says externally-managed (macOS/Linux) | Add `--break-system-packages`. |
