# gitlab-issue-bot

Webhook-Listener der neue GitLab-Issues in Echtzeit klassifiziert und mit Labels versieht.

## Was er macht

Sobald ein neues Issue geöffnet wird, analysiert der Bot Titel und Beschreibung per LLM und setzt automatisch:
- `type::bug` / `type::feature` / `type::question` / `type::documentation` / `type::other`
- `ki-ersteinschätzung::hoch` / `ki-ersteinschätzung::mittel` / `ki-ersteinschätzung::niedrig`

Zusätzlich wird ein Kommentar mit der Einschätzung ins Issue gepostet.

Issues die bereits `type::*` oder `bot::*` Labels haben werden übersprungen.

## Pipeline-Kontext

```
Neues Issue
    → gitlab-issue-bot   (type::* + ki-ersteinschätzung::*)
    → gitlab-issue-analyzer  (+ bot::prio-gesetzt)
    → gitlab-issue-solver    (+ bot::lösungsvorschlag)
```

## Endpoints

| Endpoint | Beschreibung |
|----------|-------------|
| `POST /webhook` | GitLab Webhook-Empfänger |
| `GET /webhook` | GitLab Verbindungstest |
| `POST /backfill?project_id=X` | Klassifiziert alle bestehenden Issues ohne Labels |
| `GET /health` | Health-Check |

## Setup

### 1. Repo klonen und .env anlegen

```bash
git clone https://github.com/DESM0NDw/gitlab-issue-bot
cd gitlab-issue-bot
cp .env.example .env
```

`.env` ausfüllen:

```env
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=your_gitlab_token
WEBHOOK_SECRET=your_secret

LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_api_key
```

### 2. Deployen

```bash
docker compose up -d --build
```

### 3. GitLab Webhook einrichten

In GitLab unter **Settings → Webhooks**:
- URL: `https://your-domain/webhook`
- Trigger: **Issues events**
- Secret Token: Wert aus `WEBHOOK_SECRET`

### 4. Bestehende Issues klassifizieren (optional)

```bash
curl -X POST "https://your-domain/backfill?project_id=YOUR_PROJECT_ID"
```

## Konfiguration

| Variable | Standard | Beschreibung |
|----------|----------|-------------|
| `GITLAB_URL` | `https://gitlab.com` | GitLab-Instanz URL |
| `GITLAB_TOKEN` | — | Personal Access Token (Scope: api) |
| `WEBHOOK_SECRET` | leer | Webhook-Secret (optional) |
| `LLM_PROVIDER` | `groq` | `groq` / `openai` / `mistral` |
| `GROQ_API_KEY` | — | API-Key für Groq |
| `OPENAI_API_KEY` | — | API-Key für OpenAI |
| `MISTRAL_API_KEY` | — | API-Key für Mistral |
