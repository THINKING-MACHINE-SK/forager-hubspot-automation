from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from app.config import get_settings
from app.clients.forager import ForagerClient

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
    print("Received Company Webhook Event:", body, flush=True)
    
    try:
        # Extracting domain (Webhook's test via body)
        domain = body.get("propertyValue", "openai.com")
        
        forager_client = ForagerClient()
        settings = get_settings()

        # Discovering 5 contacts from allowed job titles
        allowed_titles = settings.job_titles
        role_title = allowed_titles[0] if allowed_titles else "engineer"
        
        search_result = await forager_client.search_person_role(
            role_title=role_title,
            organization_domains=[domain]
        )
        print("Forager Search Success:", search_result, flush=True)
        
    except Exception as e:
        print("Error in company enrichment:", str(e), flush=True)

    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})

@app.post("/webhook/contact")
async def contact_webhook(request: Request):
    """
    HubSpot Contact Created/Updated Webhook Receiver
    """
    body = await request.json()
    print("Received Contact Webhook Event:", body)
    
    try:
        # Contact ke liye work email ya LinkedIn identifier lookup karna
        forager_client = ForagerClient()
        # Example lookup call using Forager client
        # await forager_client.lookup_work_email("sample_linkedin_id")
        pass
    except Exception as e:
        print("Error processing contact webhook:", str(e))
    
    return JSONResponse(status_code=status.HTTP_200_OK, content={"received": True})