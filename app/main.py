from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.services.enrichment import EnrichmentService

app = FastAPI(title="Forager × HubSpot Automation")

@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "environment": settings.app_env,
    }

@app.post("/webhook/company")
async def company_webhook(request: Request):
    body = await request.json()
    print("Received Company Webhook Event:", body, flush=True)
    
    domain = body.get("propertyValue", "openai.com")
    
    # Background service trigger karna
    enrichment_service = EnrichmentService()
    await enrichment_service.enrich_company_and_contacts(domain)
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True, "status": "processing"})
