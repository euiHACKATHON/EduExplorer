# Deploying the backend

This gets the FastAPI backend running somewhere with a public URL, so your
teammate's Replit frontend can call it instead of `localhost`. Steps below
are for [Render](https://render.com) (free tier, simplest option); Railway
works almost identically if you'd rather use that.

---

## Before you start: read this about SQLite

The database is still SQLite (Postgres migration is paused — see
`PROGRESS.md`). That has one real consequence for deployment:

**On most free-tier PaaS platforms, the filesystem is ephemeral.** Every
time you redeploy (push a new commit), the SQLite file gets wiped and
recreated empty. Restarts *within* the same deploy (e.g. the service
spinning back up after being idle) usually keep the file, but a new deploy
does not.

For a class demo, this is probably fine — just know that pushing a fix the
morning of your demo means every registered student and all their progress
is gone, and you'll want to re-register a demo account fresh. If you need
progress to survive redeploys, the options are: Render's paid persistent
disk add-on, or finishing the paused Postgres migration. Not needed today,
just don't be surprised by it.

---

## 1. Push your latest code

Deployment builds from GitHub, so make sure `main` has everything:
```powershell
git push
```

## 2. Create the service on Render

1. [render.com](https://render.com) → New → **Web Service**.
2. Connect your GitHub account, select the `EduExplorer` repo.
3. Render should auto-detect the `Dockerfile` at the repo root and set
   **Environment: Docker**. If it doesn't, set it manually.
4. Region: whichever's closest to you. Instance type: **Free** is fine for
   a demo.
5. Don't deploy yet — set environment variables first (next step), then
   click **Create Web Service**.

## 3. Environment variables

In the Render dashboard, under **Environment**, add:

| Key | Value | Notes |
|---|---|---|
| `AUTH_SECRET` | a long random string | Generate one: `python -c "import secrets; print(secrets.token_hex(32))"`. Do not reuse the dev default. |
| `GROQ_API_KEY` | your real Groq key | AI features silently fall back to authored content without this — not an error, just less impressive in a demo. |
| `ALLOWED_ORIGINS` | your Replit frontend's exact URL | e.g. `https://your-repl-name.username.repl.co`. No trailing slash. Comma-separate if there's more than one (e.g. keep `http://localhost:5173` too for local frontend dev against the deployed backend). |

`MARS_DB` and `OPENAI_API_KEY` don't need to be set — the first defaults to
a path inside the container (see the SQLite note above), the second isn't
read anywhere anymore.

## 4. Health check

Render lets you set a health check path — use `/health`. It already exists
and returns `{"status": "ok", "ai_available": ..., "provider": "groq"}`.

## 5. Deploy and get your URL

Render builds the Docker image and deploys. You'll get a URL like
`https://your-service-name.onrender.com`. Test it:
```powershell
curl https://your-service-name.onrender.com/health
```

Give this URL to whoever owns the Replit frontend — it's the API base URL
they point their fetch calls at.

## 6. One demo-day gotcha: cold starts

Render's free tier spins the service down after ~15 minutes of no traffic.
The next request after that wakes it back up, but takes 30-60 seconds. If
you're demoing live, hit `/health` a minute or two beforehand so it's
already warm when people are watching.

## 7. Redeploying

Render redeploys automatically on every push to `main` by default (check
this under **Settings** if you want to turn it off and deploy manually
instead). Remember: every redeploy resets the SQLite data (see the note at
the top).

---

## Checklist before your demo

- [ ] `ALLOWED_ORIGINS` matches the *exact* frontend URL you'll actually be
      using that day (Replit URLs can change between the dev preview and
      a published deployment — check which one you're demoing from).
- [ ] `GROQ_API_KEY` is set and has quota left.
- [ ] Hit `/health` a few minutes before to wake the service up.
- [ ] Register a fresh demo student account after the last deploy before
      the demo, so you're not relying on data from a previous test run.
