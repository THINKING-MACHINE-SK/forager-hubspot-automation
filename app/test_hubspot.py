import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.clients.hubspot import HubSpotClient
from app.services.enrichment import EnrichmentService


def mock_hubspot(monkeypatch, handler):
    async_client = httpx.AsyncClient
    transport = httpx.MockTransport(handler)
    monkeypatch.setattr(
        "app.clients.hubspot.httpx.AsyncClient",
        lambda **kwargs: async_client(transport=transport, **kwargs),
    )
    client = HubSpotClient.__new__(HubSpotClient)
    client.headers = {"Authorization": "Bearer test-token"}
    return client


@pytest.mark.parametrize("duplicate", [False, True])
def test_contact_creation_and_duplicate_skip(monkeypatch, duplicate):
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(409 if duplicate else 201, json={"id": "42"})
        assert request.method == "PUT"
        assert request.url.path.endswith("/contacts/42/associations/companies/7/contact_to_company")
        return httpx.Response(204)

    client = mock_hubspot(monkeypatch, handler)
    contact_id = asyncio.run(
        client.create_contact("jane+demo@example.com", "Jane", "Doe", "7")
    )
    assert contact_id == (None if duplicate else "42")
    assert [call.method for call in calls] == (
        ["POST"] if duplicate else ["POST", "PUT"]
    )


@pytest.mark.parametrize("status_code", [401, 403, 429, 500])
def test_non_duplicate_errors_still_raise(monkeypatch, status_code):
    def handler(request):
        assert request.method == "POST"
        return httpx.Response(status_code)

    client = mock_hubspot(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError) as error:
        asyncio.run(client.create_contact("jane@example.com", "Jane", "Doe"))
    assert error.value.response.status_code == status_code


def test_missing_contact_id_still_raises(monkeypatch):
    def handler(request):
        return httpx.Response(201, json={})

    client = mock_hubspot(monkeypatch, handler)
    with pytest.raises(ValueError, match="did not include an ID"):
        asyncio.run(client.create_contact("jane@example.com", "Jane", "Doe", "7"))


def test_repeated_webhook_skips_duplicate_and_finishes_pipeline(monkeypatch):
    from app import main

    contacts = set()
    associated = []

    def handler(request):
        if request.method == "POST" and request.url.path.endswith("/companies"):
            return httpx.Response(201, json={"id": "7"})
        if request.method == "POST":
            import json

            email = json.loads(request.content)["properties"]["email"]
            if email in contacts:
                return httpx.Response(409)
            contacts.add(email)
            return httpx.Response(201, json={"id": email})
        assert request.method == "PUT"
        associated.append(request.url.path)
        return httpx.Response(204)

    hubspot = mock_hubspot(monkeypatch, handler)
    service = EnrichmentService.__new__(EnrichmentService)
    service.settings = SimpleNamespace(job_titles=["engineer"])
    service.hubspot_client = hubspot
    service.forager_client = SimpleNamespace(
        search_person_role=AsyncMock(return_value={
            "search_results": [
                {"first_name": "Jane", "last_name": "Doe"},
                {"first_name": "Jane", "last_name": "Doe"},
            ],
        }),
    )
    monkeypatch.setattr(main, "EnrichmentService", lambda: service)
    with TestClient(main.app) as client:
        for _ in range(2):
            response = client.post("/webhook/company", json={
                "subscriptionType": "company.creation",
                "objectId": 12345,
                "propertyValue": "example.com",
            })
            assert response.status_code == 200
            assert response.json()["received"] is True
    assert contacts == {"jane.doe.0@example.com", "jane.doe.1@example.com"}
    assert len(associated) == 2
