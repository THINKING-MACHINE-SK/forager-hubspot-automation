from app.config import get_settings
from app.clients.forager import ForagerClient
from app.clients.hubspot import HubSpotClient


class EnrichmentService:
    def __init__(self):
        self.settings = get_settings()
        self.forager_client = ForagerClient()
        self.hubspot_client = HubSpotClient()

    async def enrich_company_and_contacts(self, domain: str):
        print(f"Starting enrichment pipeline for domain: {domain}", flush=True)

        try:
            allowed_titles = self.settings.job_titles
            role_title = allowed_titles[0] if allowed_titles else "engineer"

            search_response = await self.forager_client.search_person_role(
                role_title=role_title,
                organization_domains=[domain],
            )

            results = search_response.get("results", []) or search_response.get(
                "data", []
            )
            print(f"Found {len(results)} raw profiles from Forager.", flush=True)

            top_contacts = results[:5]

            company_name = domain.split(".")[0].capitalize()
            company_id = await self.hubspot_client.create_or_update_company(
                domain,
                company_name,
            )
            print(f"HubSpot Company ID: {company_id}", flush=True)

            for person in top_contacts:
                linkedin_id = person.get("linkedin_public_identifier")
                firstname = person.get("first_name", "Unknown")
                lastname = person.get("last_name", "")

                if linkedin_id:
                    email_response = await self.forager_client.lookup_work_email(
                        linkedin_id
                    )
                    work_email = email_response.get("email") or (
                        f"{firstname.lower()}@{domain}"
                    )

                    await self.hubspot_client.create_contact(
                        email=work_email,
                        firstname=firstname,
                        lastname=lastname,
                        company_id=company_id,
                    )
                    print(
                        f"Successfully added contact: {firstname} ({work_email}) "
                        "to HubSpot",
                        flush=True,
                    )

        except Exception as e:
            print(f"Error in enrichment pipeline: {e}", flush=True)
            raise
