import httpx

from app.config import get_settings


class HubSpotClient:
    BASE_URL = "https://api.hubapi.com"

    def __init__(self) -> None:
        settings = get_settings()
        self.headers = {
            "Authorization": f"Bearer {settings.hubspot_access_token}",
            "Content-Type": "application/json",
        }

    async def get_company(self, company_id: str) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{self.BASE_URL}/crm/v3/objects/companies/{company_id}",
                headers=self.headers,
                params={"properties": "name,domain,description,numberofemployees"},
            )
            response.raise_for_status()
            return response.json()

    async def update_company(
        self,
        company_id: str,
        properties: dict,
    ) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(
                f"{self.BASE_URL}/crm/v3/objects/companies/{company_id}",
                headers=self.headers,
                json={"properties": properties},
            )
            response.raise_for_status()
            return response.json()

    async def update_contact(
        self,
        contact_id: str,
        properties: dict,
    ) -> dict:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.patch(
                f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}",
                headers=self.headers,
                json={"properties": properties},
            )
            response.raise_for_status()
            return response.json()