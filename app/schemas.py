from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EnrichedContact(BaseModel):
    model_config = ConfigDict(extra="ignore")

    first_name: str = Field(min_length=1)
    last_name: str = Field(min_length=1)
    linkedin_url: HttpUrl | None = None
    job_title: str | None = None
    company_name: str | None = None
    company_domain: str | None = None
    company_linkedin_url: HttpUrl | None = None
    email: str | None = None
    phone: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None


class EnrichedCompany(BaseModel):
    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=1)
    domain: str | None = None
    linkedin_url: HttpUrl | None = None
    description: str | None = None
    revenue: str | None = None
    headcount: int | None = None
    