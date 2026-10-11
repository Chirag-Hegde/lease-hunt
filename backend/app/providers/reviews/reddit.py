"""Reddit official API provider (OAuth client-credentials via httpx).
Searches relevant city subreddits for the building/management company."""

from datetime import UTC, datetime

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.providers.reviews.base import ReviewDoc

_SUBREDDITS = ["bayarea", "SanJose", "sunnyvale", "SantaClara"]
_USER_AGENT = "LeaseLens/0.1 (building review research)"


class RedditProvider:
    name = "reddit"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._token: str | None = None

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if self._token:
            return self._token
        resp = await client.post(
            "https://www.reddit.com/api/v1/access_token",
            auth=(self._client_id, self._client_secret),
            data={"grant_type": "client_credentials"},
            headers={"User-Agent": _USER_AGENT},
        )
        resp.raise_for_status()
        token: str = resp.json()["access_token"]
        self._token = token
        return token

    async def fetch(
        self, building_key: str, building_name: str | None, session: AsyncSession
    ) -> list[ReviewDoc]:
        query = building_name or building_key
        docs: list[ReviewDoc] = []
        async with httpx.AsyncClient(timeout=15) as client:
            token = await self._get_token(client)
            for subreddit in _SUBREDDITS:
                resp = await client.get(
                    f"https://oauth.reddit.com/r/{subreddit}/search",
                    params={"q": query, "restrict_sr": 1, "limit": 10, "sort": "new"},
                    headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": _USER_AGENT,
                    },
                )
                if resp.status_code != 200:
                    continue
                for child in resp.json().get("data", {}).get("children", []):
                    post = child.get("data", {})
                    text = f"{post.get('title', '')}\n{post.get('selftext', '')}".strip()
                    if not text:
                        continue
                    docs.append(
                        ReviewDoc(
                            source_type="reddit",
                            external_id=post.get("name"),
                            url=f"https://www.reddit.com{post.get('permalink', '')}",
                            author=post.get("author"),
                            text=text[:2000],
                            posted_at=datetime.fromtimestamp(post.get("created_utc", 0), tz=UTC),
                        )
                    )
        return docs
