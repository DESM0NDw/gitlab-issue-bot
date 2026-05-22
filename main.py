import hmac
import hashlib
import logging
from fastapi import FastAPI, Request, HTTPException, Header
from classifier import classify_issue
from gitlab_client import set_labels, post_comment, fetch_unclassified_issues
from config import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = FastAPI(title="GitLab Issue Bot")

# ki-ersteinschätzung = vorläufige Einschätzung bei Issue-Erstellung
# Endgültige Priorität kommt vom Analyzer in der Prioritätsliste
PRIORITY_LABELS = {
    "Hoch": "ki-ersteinschätzung::hoch",
    "Mittel": "ki-ersteinschätzung::mittel",
    "Niedrig": "ki-ersteinschätzung::niedrig",
}
CATEGORY_LABELS = {
    "Bug": "type::bug",
    "Feature": "type::feature",
    "Frage": "type::question",
    "Dokumentation": "type::documentation",
    "Sonstiges": "type::other",
}


def _verify_secret(token: str | None) -> None:
    if not settings.webhook_secret:
        return
    if not token or not hmac.compare_digest(token, settings.webhook_secret):
        raise HTTPException(status_code=401, detail="Ungültiges Webhook-Secret")


@app.post("/webhook")
async def webhook(request: Request, x_gitlab_token: str | None = Header(None)):
    _verify_secret(x_gitlab_token)

    payload = await request.json()

    if payload.get("object_kind") != "issue":
        return {"status": "ignored"}

    attrs = payload.get("object_attributes", {})
    if attrs.get("action") != "open":
        return {"status": "ignored"}

    project_id = payload["project"]["id"]
    issue_iid = attrs["iid"]
    title = attrs.get("title", "")
    description = attrs.get("description", "")

    log.info(f"Neues Issue #{issue_iid}: {title}")

    try:
        result = await classify_issue(title, description)
    except Exception as e:
        log.error(f"Klassifizierung fehlgeschlagen: {e}")
        raise HTTPException(status_code=500, detail="LLM-Fehler")

    category = result.get("category", "Sonstiges")
    priority = result.get("priority", "Mittel")
    comment_text = result.get("comment", "")

    labels = ["bot::analysiert"]
    if label := CATEGORY_LABELS.get(category):
        labels.append(label)
    if label := PRIORITY_LABELS.get(priority):
        labels.append(label)

    await set_labels(project_id, issue_iid, labels)

    comment = (
        f"**KI-Analyse**\n\n"
        f"- **Kategorie:** {category}\n"
        f"- **Priorität:** {priority}\n\n"
        f"{comment_text}\n\n"
        f"---\n*Automatisch generiert von gitlab-issue-bot*"
    )
    await post_comment(project_id, issue_iid, comment)

    log.info(f"Issue #{issue_iid} klassifiziert: {category}, {priority}")
    return {"status": "ok", "category": category, "priority": priority}


@app.get("/webhook")
async def webhook_check():
    return {"status": "ok"}


@app.post("/backfill")
async def backfill(project_id: str):
    issues = await fetch_unclassified_issues(project_id)
    if not issues:
        return {"status": "ok", "message": "Keine Issues ohne Klassifizierung gefunden"}

    processed = 0
    for issue in issues:
        try:
            result = await classify_issue(issue["title"], issue.get("description", ""))
            category = result.get("category", "Sonstiges")
            priority = result.get("priority", "Mittel")
            comment_text = result.get("comment", "")

            labels = ["bot::analysiert"]
            if label := CATEGORY_LABELS.get(category):
                labels.append(label)
            if label := PRIORITY_LABELS.get(priority):
                labels.append(label)

            await set_labels(project_id, issue["iid"], labels)
            comment = (
                f"**KI-Analyse** (nachträglich)\n\n"
                f"- **Kategorie:** {category}\n"
                f"- **Priorität (Ersteinschätzung):** {priority}\n\n"
                f"{comment_text}\n\n"
                f"---\n*Automatisch generiert von gitlab-issue-bot*"
            )
            await post_comment(project_id, issue["iid"], comment)
            processed += 1
            log.info(f"Backfill Issue #{issue['iid']}: {category}, {priority}")
        except Exception as e:
            log.error(f"Backfill fehlgeschlagen für Issue #{issue['iid']}: {e}")

    return {"status": "ok", "processed": processed}


@app.get("/health")
async def health():
    return {"status": "ok"}
