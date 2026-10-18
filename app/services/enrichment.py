import httpx
from app.config import get_settings
from app.clients.forager import ForagerClient

class EnrichmentService:
    def __init__(self):
        self.settings = get_settings()
        self.forager_client = ForagerClient()

    async def enrich_company_and_contacts(self, domain: str):
        """
        1. Forager API se specific domain ke liye contacts search karna
        2. Top 5 contacts filter karna
        3. HubSpot CRM mein company aur contacts create/update karna
        """
        print(f"Starting enrichment for domain: {domain}", flush=True)
        
        # Step 1: Forager Person Role Search
        # Allowed job titles ko use karke search karenge
        allowed_titles = self.settings.job_titles
        role_title = allowed_titles[0] if allowed_titles else "engineer"
        
        try:
            search_response = await self.forager_client.search_person_role(
                role_title=role_title,
                organization_domains=[domain]
            )
            print("Forager Search Results Received:", search_response, flush=True)
            
            # Yahan se aapko contacts ki list milegi (Forager API response structure ke mutabik)
            # Hum top 5 contacts extract karenge aur unke work emails lookup karenge
            
        except Exception as e:
            print("Error during Forager enrichment:", str(e), flush=True)
            raise e
        