from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.config import get_settings

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
    """
    HubSpot Company Created/Updated Webhook Receiver
    """
    body = await request.json()
    print("Received Company Webhook Event:", body)
    
    # Yahan aap apna enrichment service call karenge:
    # 1. Company domain nikalenge
    # 2. Forager API se company details fetch karenge
    # 3. HubSpot API ke through company update karenge aur 5 contacts discover/enrich karenge
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})

@app.post("/webhook/contact")
async def contact_webhook(request: Request):
    """
    HubSpot Contact Created/Updated Webhook Receiver
    """
    body = await request.json()
    print("Received Contact Webhook Event:", body)
    
    # Yahan aap contact enrichment logic likhenge:
    # 1. Contact ka LinkedIn URL ya email lenge
    # 2. Forager se contact details enrich karenge
    # 3. HubSpot CRM contact properties update karenge
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})