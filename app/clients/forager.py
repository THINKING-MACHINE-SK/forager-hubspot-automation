import httpx
from app.config import get_settings

class ForagerClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.forager_base_url.rstrip("/")
        # Forager uses 'X-API-KEY' header based on their API docs
        self.headers = {
            "X-API-KEY": settings.forager_api_key,
            "Content-Type": "application/json",
        }

    async def search_person_role(self, role_title: str, organization_domains: list[str]) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/datastorage/person_role_search/",
                headers=self.headers,
                json={
                    "role_title": role_title,
                    "organization_domains": organization_domains
                }
            )
            response.raise_for_status()
            return response.json()

    async def lookup_work_email(self, linkedin_public_identifier: str) -> dict:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/datastorage/person_contacts_lookup/work_emails/",
                headers=self.headers,
                json={"linkedin_public_identifier": linkedin_public_identifier}
            )
            response.raise_for_status()
            return response.json()