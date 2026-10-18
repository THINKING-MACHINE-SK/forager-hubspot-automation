# Forager–HubSpot Automation

A FastAPI service that receives a company webhook, searches Forager for people at the company, creates HubSpot contacts, and associates those contacts with a HubSpot company.

This README documents the current implementation, the changes made while debugging it, and why those changes were needed.

## Project structure

| File | Purpose |
| --- | --- |
| `app/main.py` | FastAPI application, health endpoint, and company webhook. |
| `app/config.py` | Environment configuration and comma-separated job-title parsing. |
| `app/clients/forager.py` | Forager role-search and work-email lookup requests. |
| `app/clients/hubspot.py` | HubSpot company/contact requests, duplicate resolution, and associations. |
| `app/services/enrichment.py` | Coordinates company creation, profile search, email generation, and contact association. |
| `app/services/contact_discovery.py` | Standalone job-title filtering helper; currently unused by the enrichment pipeline. |
| `app/schemas.py` | Company/contact Pydantic models; currently unused by the webhook handler. |
| `app/test_hubspot.py` | Mocked HubSpot and webhook regression tests. |
| `app/test_job_filter.py` | Job-title filtering test. |
| `requirements.txt` | Runtime and test dependencies. |
| `Dockerfile` | Python 3.12 container and Uvicorn startup command. |

## Setup

Use Python 3.12 to match the Docker image. From the project directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Create a `.env` file in the project root with your own values:

```dotenv
APP_ENV=development
HUBSPOT_ACCESS_TOKEN=replace-with-your-hubspot-token
FORAGER_API_KEY=replace-with-your-forager-api-key
FORAGER_BASE_URL=https://your-forager-api-host
ALLOWED_JOB_TITLES=CEO,CTO,VP Engineering,Head of AI
```

`FORAGER_BASE_URL` is a placeholder above. Use the API base URL provided for your Forager account; the client appends `/datastorage/...` paths to it. Do not commit real credentials.

| Variable | Required | Behavior |
| --- | --- | --- |
| `HUBSPOT_ACCESS_TOKEN` | Yes | Used in HubSpot's Bearer authorization header. Must permit the company/contact reads, writes, searches, and associations used by the application. |
| `FORAGER_API_KEY` | Yes | Sent through the `X-API-KEY` header. |
| `FORAGER_BASE_URL` | Yes | Base URL for Forager requests. |
| `APP_ENV` | No | Defaults to `development`; returned by `/health`. |
| `ALLOWED_JOB_TITLES` | No | Defaults to `CEO,CTO,VP Engineering,Head of AI`. Split on commas with whitespace and empty entries removed. |

Settings are cached by `get_settings()`. Restart the application after changing configuration.

Start the server:

```powershell
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Endpoints and testing a request

### Health check

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health"
```

Expected response with the example configuration:

```json
{"status": "ok", "environment": "development"}
```

This checks that the app can load its settings. It does not verify Forager or HubSpot connectivity.

### Company webhook

```powershell
$payload = @{
    subscriptionType = "company.creation"
    objectId = 12345
    propertyValue = "openai.com"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "http://localhost:8000/webhook/company" `
    -Method Post `
    -ContentType "application/json" `
    -Body $payload
```

This request performs real API operations when real credentials are configured. A successful request returns:

```json
{"received": true, "status": "processing"}
```

Despite the response label `processing`, the handler currently **awaits the entire enrichment pipeline before returning**. It does not enqueue a background job.

The handler currently expects a single JSON object and reads the domain from `propertyValue`, defaulting to `openai.com` if that key is absent. It does not use `objectId` to fetch or reuse the triggering company, validate `subscriptionType`, or process an array of webhook events. The example `objectId` is therefore illustrative.

## Current enrichment flow

1. Read the domain from the webhook.
2. Create a HubSpot company using the domain and a name derived from the domain's first segment.
3. Search Forager using each configured title in order. If the configured title list is empty, try `engineer`, `founder`, and `manager`.
4. Log the response and extract profiles from the first non-empty supported result key, or accept a direct list response.
5. Stop searching after the first title that returns profiles. A search exception is logged and the next title is tried.
6. Select the first five profiles. For `openai.com` only, use the two hardcoded demo profiles if no profiles were found.
7. Generate an email for each selected profile and attempt contact creation.
8. If HubSpot returns `409 Conflict`, search for the existing contact by email and obtain its ID.
9. Associate the new or existing contact with the company, then continue to the next profile.

All title searches use the submitted domain. There is currently no fallback-domain list and no merging of results from multiple titles.

## Changes made and why

| Area | Change made | Why |
| --- | --- | --- |
| Webhook integration | Connected `/webhook/company` to `EnrichmentService`. | Allow an incoming request to trigger the complete Forager-to-HubSpot flow. |
| Forager client | Added role search at `/datastorage/person_role_search/` and work-email lookup at `/datastorage/person_contacts_lookup/work_emails/`, using `X-API-KEY`. | Separate API requests from orchestration and support profile/email lookup. The work-email method remains available but is not called by the current pipeline. |
| Response debugging | Added response logs for each searched title and a total-profile count, with `flush=True`. | Make the actual API structure and search outcomes visible in server logs without waiting for output buffering. |
| Result parsing | Added support for `results`, `data`, `items`, and direct lists; later placed `search_results` first. | The observed Forager response used `search_results`, so the older parser missed successfully returned profiles. |
| List handling | Check `isinstance(search_response, list)` before calling `.get()`. | Avoid an attribute error when Forager returns a list instead of a dictionary. |
| Title retries | Replaced the single-title search with a loop that tries configured titles until profiles are found. | One title can return no matches; another can produce useful results. |
| Company creation | Moved company creation before the searches and contact loop. | Obtain the company ID needed for contact associations. |
| Contact limit | Process only `search_results[:5]`. | Keep each enrichment request bounded to five contacts. |
| Demo fallback | Added hardcoded Sam Altman and Mira Murati profiles when `openai.com` returns no profiles. | Support a demo when real search results are unavailable. These are sample records, not verified employment or contact data. |
| Email generation | Replaced the earlier shared/default-name address with `firstname.lastname.idx@domain`. | Distinguish same-name contacts within one batch and avoid every missing-name profile using `valued.contact@openai.com`. |
| Missing names | Use `User` for a missing/empty first name and the profile index for a missing/empty last name. | Avoid calling `.lower()` on `None` and still generate an address for incomplete profiles. |
| Initial duplicate diagnosis | Identified HubSpot contact creation as the source of the reported `500`; the upstream API returned `409 Conflict` after Forager had returned seven profiles. | Confirm that successful Forager searches did not mean the downstream CRM operation had succeeded. |
| Duplicate handling revisions | Initially added existing-contact lookup; temporarily changed to logging and returning `None` on `409`; finally restored lookup using the contact search endpoint. | Skipping the duplicate prevented that exception but also skipped its company association. The final implementation reuses the contact ID and performs the association. |
| Error handling | Keep `raise_for_status()` for failed creation, search, and association requests; reject empty search results or missing contact IDs. | Avoid silently reporting success when the required contact or association could not be resolved. |
| Regression tests | Added mocked contact and repeated-webhook tests, then updated them as duplicate behavior changed. | Verify that existing contacts are associated and unrelated API failures still surface. |

### Final response parsing order

For a dictionary response, the service checks the first non-empty value in this order:

```text
search_results -> results -> data -> items -> []
```

A direct list bypasses dictionary-key lookup. Dictionary result values are expected to be lists of profile dictionaries; arbitrary nested response formats are not normalized.

### Email generation

The current logic is:

```python
for idx, person in enumerate(top_contacts):
    firstname = person.get("first_name") or "User"
    lastname = person.get("last_name") or str(idx)
    email = f"{firstname.lower()}.{lastname.lower()}.{idx}@{domain}".replace(" ", "")
```

For example, two profiles named Jane Doe generate `jane.doe.0@openai.com` and `jane.doe.1@openai.com`.

These are **generated demo addresses, not verified work emails**. The index makes them distinct within a batch, not globally unique across requests. Repeating the same ordered profiles generates the same addresses; `409` handling then resolves existing contacts. Reordering profiles can generate different addresses for the same person. The code currently expects flat `first_name` and `last_name` fields and does not normalize nested person records.

### Final duplicate-contact behavior

`HubSpotClient.create_contact()` uses this sequence:

```text
POST /crm/v3/objects/contacts
  success -> read contact ID
  409     -> POST /crm/v3/objects/contacts/search
             filter: email EQ supplied_email
             use first returned contact ID

If company_id is supplied:
  PUT /crm/v3/objects/contacts/{contactId}/associations/companies/{companyId}/contact_to_company

Return contact ID
```

The current client defines `BASE_URL = "https://api.hubapi.com"` and appends `/crm/v3/...`. Snippets referring to `self.base_url` must be adapted to this class; that instance attribute is not defined here.

The search does not update existing contact names. A failed search, no matching record, missing ID, or failed association raises an error. There is no search retry/backoff, so an existing record that is not yet visible in search can still cause a failure.

## Tests

Run from the project root:

```powershell
python -m pytest -q
```

The latest implementation test run completed with **13 passed** and one dependency deprecation warning from Starlette's test client. Coverage includes:

- New contact creation and company association.
- Duplicate contact lookup and company association.
- Propagation of `401`, `403`, `429`, and `500` creation errors.
- Missing IDs and empty or failed duplicate searches.
- Repeated webhook requests that associate existing contacts and complete successfully.
- Different generated emails for same-name profiles in one batch.
- The standalone job-title filtering helper.

HubSpot and Forager calls in these tests are mocked. Passing tests do not verify live credentials or the deployed Railway service.

## Docker and Railway

Build and run locally:

```powershell
docker build -t forager-hubspot-automation .
docker run --rm --env-file .env -p 8000:8000 forager-hubspot-automation
```

The Dockerfile starts Uvicorn on `0.0.0.0`, using `PORT` when provided and `8000` otherwise. For Railway, configure the environment variables above in the service and deploy the updated source through your existing deployment workflow.

The deployment URL used during debugging was:

```text
https://forager-hubspot-automation-production.up.railway.app
```

To run the webhook example against that deployment, replace `http://localhost:8000` with this URL. Local edits do not change Railway until the service deploys the updated code. The README does not assert that the deployed service has been updated or verified.

## Troubleshooting and current limits

| Observation | Meaning / next check |
| --- | --- |
| `Total profiles found: 7` | Forager returned profiles that the parser recognized. The contact limit means at most five are processed. Check later HubSpot logs if the request fails. |
| `409 Conflict` followed by `Fetching existing contact ID...` | Expected duplicate-recovery path. Confirm that search returns an ID and the subsequent association succeeds. |
| Logs still show `valued.contact@openai.com` | The current local generator no longer emits that address. Confirm the deployed source includes the email-generation update. |
| `401` or `403` | Check the credentials and permissions for the API named in the exception. |
| Duplicate reported but email search returns no match | The contact could not be resolved by the implemented search. Inspect the upstream response and search visibility before retrying. |
| Generic webhook `500` | Read the server traceback and `Error in enrichment pipeline` log. Exceptions still propagate to FastAPI; the handler does not return structured upstream error details. |

Additional implementation limits:

- `create_or_update_company()` currently always sends a create request, despite its name. It does not search for or update an existing company, and repeated webhooks can create additional company records.
- The handler does not verify webhook signatures, deduplicate events, or queue durable background work.
- The pipeline stops at a contact creation/association exception; it does not roll back prior CRM writes or continue with later contacts after that failure.
- Search failures for all titles are logged and can still lead to the demo fallback or an empty contact list. A successful webhook response is therefore not proof that live profiles were found.
- Full webhook and Forager response logging can include profile data. Review logging needs before using production data.
