import httpx
from config import settings

HEADERS = {"PRIVATE-TOKEN": settings.gitlab_token}


def _project_url(project_id: str | int) -> str:
    return f"{settings.gitlab_url}/api/v4/projects/{project_id}"


async def set_labels(project_id: str | int, issue_iid: int, labels: list[str]) -> None:
    async with httpx.AsyncClient() as client:
        await client.put(
            f"{_project_url(project_id)}/issues/{issue_iid}",
            headers=HEADERS,
            json={"labels": ",".join(labels)},
            timeout=10,
        )


async def post_comment(project_id: str | int, issue_iid: int, body: str) -> None:
    async with httpx.AsyncClient() as client:
        await client.post(
            f"{_project_url(project_id)}/issues/{issue_iid}/notes",
            headers=HEADERS,
            json={"body": body},
            timeout=10,
        )


async def fetch_unclassified_issues(project_id: str | int) -> list[dict]:
    issues = []
    page = 1
    async with httpx.AsyncClient() as client:
        while True:
            response = await client.get(
                f"{_project_url(project_id)}/issues",
                headers=HEADERS,
                params={
                    "state": "opened",
                    "not[labels]": "type::bug,type::feature,type::question,type::documentation,type::other",
                    "per_page": 100,
                    "page": page,
                },
                timeout=15,
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            issues.extend(batch)
            page += 1
    return issues
