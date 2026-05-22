import json
import httpx
from config import settings, LLM_CONFIG

SYSTEM_PROMPT = """Du bist ein Issue-Triage-Assistent. Analysiere das GitLab-Issue und antworte ausschließlich mit JSON:
{
  "category": "Bug" | "Feature" | "Frage" | "Dokumentation" | "Sonstiges",
  "priority": "Hoch" | "Mittel" | "Niedrig",
  "comment": "1-2 Sätze Einschätzung auf Deutsch"
}"""


async def classify_issue(title: str, description: str) -> dict:
    cfg = LLM_CONFIG.get(settings.llm_provider)
    if not cfg:
        raise ValueError(f"Unbekannter LLM-Provider: {settings.llm_provider}")

    api_key = getattr(settings, cfg["api_key_field"])
    if not api_key:
        raise ValueError(f"Kein API-Key für {settings.llm_provider} gesetzt")

    prompt = f"Titel: {title}\n\nBeschreibung: {description or '(keine Beschreibung)'}"

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{cfg['base_url']}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": cfg["model"],
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
            },
            timeout=30,
        )
        response.raise_for_status()

    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)
