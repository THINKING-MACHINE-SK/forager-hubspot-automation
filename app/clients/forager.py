import httpx
from app.config import get_settings

class ForagerClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.forager_base_url.rstrip("/")
        # Forager API key ke liye X-API-KEY header use karta hai
        self.headers = {
            "X-API-KEY": settings.forager_api_key,
            "Content-Type": "application/json",
        }

    async def _post(self, path: str, payload: dict) -> dict:
        url = f"{self.base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def enrich_company(self, domain: str) -> dict:
        """Company enrichment ke liye organization search endpoint use karenge."""
        path = "/datastorage/organization_search/"
        payload = {"domain": domain}
        return await self._post(path, payload)

    async def enrich_contact(self, linkedin_identifier: str) -> dict:
        """Contact detail lookup ke liye person detail lookup endpoint."""
        path = "/datastorage/person_detail_lookup/"
        payload = {"linkedin_public_identifier": linkedin_identifier}
        return await self._post(path, payload)

    async def find_contacts(self, company_domain: str, job_titles: list[str]) -> dict:
        """Company ke andar job titles ke basis par contacts search karna."""
        path = "/datastorage/person_role_search/"
        payload = {
            "organization_domain": company_domain,
            "job_titles": job_titles
        }
        return await self._post(path, payload)