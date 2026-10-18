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
def test_contact_creation_and_duplicate_recovery(monkeypatch, duplicate):
    calls = []

    def handler(request):
        calls.append(request)
        if request.method == "POST":
            return httpx.Response(409 if duplicate else 201, json={"id": "42"})
        if request.method == "GET":
            assert request.url.params["idProperty"] == "email"
            assert request.url.path.endswith("/jane+demo@example.com")
            return httpx.Response(200, json={"id": "42"})
        assert request.method == "PUT"
        assert request.url.path.endswith("/contacts/42/associations/companies/7/contact_to_company")
        return httpx.Response(204)

    client = mock_hubspot(monkeypatch, handler)
    contact_id = asyncio.run(
        client.create_contact("jane+demo@example.com", "Jane", "Doe", "7")
    )
    assert contact_id == "42"
    assert [call.method for call in calls] == (
        ["POST", "GET", "PUT"] if duplicate else ["POST", "PUT"]
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


def test_failed_duplicate_lookup_still_raises(monkeypatch):
    def handler(request):
        return httpx.Response(409 if request.method == "POST" else 404)

    client = mock_hubspot(monkeypatch, handler)
    with pytest.raises(httpx.HTTPStatusError) as error:
        asyncio.run(client.create_contact("jane@example.com", "Jane", "Doe", "7"))
    assert error.value.response.status_code == 404


def test_repeated_webhook_reuses_contact_and_finishes_pipeline(monkeypatch):
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
        if request.method == "GET":
            return httpx.Response(200, json={"id": request.url.path.rsplit("/", 1)[-1]})
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
                {"first_name": "John", "last_name": "Doe"},
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
    assert len(contacts) == 2
    assert len(associated) == 4
