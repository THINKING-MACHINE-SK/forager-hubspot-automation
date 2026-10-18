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

    async def create_or_update_company(self, domain: str, name: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/crm/v3/objects/companies",
                headers=self.headers,
                json={
                    "properties": {
                        "domain": domain,
                        "name": name or domain,
                    }
                },
            )
            response.raise_for_status()
            company_id = response.json().get("id")
            if not company_id:
                raise ValueError("HubSpot company response did not include an ID")
            return str(company_id)

    async def create_contact(
        self,
        email: str,
        firstname: str,
        lastname: str,
        company_id: str | None = None,
    ) -> str:
        """Create or find a contact and associate it with the supplied company."""
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.BASE_URL}/crm/v3/objects/contacts",
                headers=self.headers,
                json={
                    "properties": {
                        "email": email,
                        "firstname": firstname,
                        "lastname": lastname,
                    }
                },
            )
            if response.status_code == 409:
                print(
                    f"Contact with email {email} already exists (409 Conflict). "
                    "Fetching existing contact ID...",
                    flush=True,
                )
                response = await client.post(
                    f"{self.BASE_URL}/crm/v3/objects/contacts/search",
                    headers=self.headers,
                    json={
                        "filterGroups": [{
                            "filters": [{
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": email,
                            }],
                        }],
                        "limit": 1,
                    },
                )
                response.raise_for_status()
                results = response.json().get("results", [])
                if not results:
                    raise ValueError(
                        "HubSpot reported a duplicate contact, but email search "
                        "returned no matching contact"
                    )
                contact_id = results[0].get("id")
            else:
                response.raise_for_status()
                contact_id = response.json().get("id")
            if not contact_id:
                raise ValueError("HubSpot contact response did not include an ID")

            if company_id:
                await self.associate_contact_to_company(str(contact_id), company_id)
            return str(contact_id)

    async def associate_contact_to_company(
        self,
        contact_id: str,
        company_id: str,
    ) -> bool:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.put(
                f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
                f"/associations/companies/{company_id}/contact_to_company",
                headers=self.headers,
            )
            response.raise_for_status()
            return response.status_code == 204

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
