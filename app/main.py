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
    print("Received Company Webhook Event:", body)
    
    try:
        # 1. Webhook payload se company ki details ya domain nikalna (HubSpot structure ke mutabik)
        # 2. Forager API ke zariye role search ya company data fetch karna
        forager_client = ForagerClient()
        
        # Example: Allowed job titles par 5 contacts discover karna
        settings = get_settings()
        allowed_titles = settings.job_titles
        
        # Test/Demo domain (Jaise openai.com) par job titles search karna
        # (Aap isko webhook ke incoming domain se bhi dynamic bana sakte hain)
        search_result = await forager_client.search_person_role(
            role_title=allowed_titles[0] if allowed_titles else "engineer",
            organization_domains=["openai.com"]
        )
        print("Forager Search Result:", search_result)
        
    except Exception as e:
        print("Error processing company webhook:", str.e if hasattr(e, 'e') else str(e))

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