from fastapi import FastAPI

app = FastAPI(title="Forager × HubSpot Automation")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}