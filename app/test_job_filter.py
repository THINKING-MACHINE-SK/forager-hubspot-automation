from app.services.contact_discovery import filter_contacts_by_title


def test_filter_contacts_by_allowed_titles():
    contacts = [
        {"job_title": "CEO"},
        {"job_title": "Software Engineer"},
        {"job_title": "CTO"},
        {"job_title": None},
    ]

    result = filter_contacts_by_title(contacts, ["CEO", "CTO"])

    assert result == [
        {"job_title": "CEO"},
        {"job_title": "CTO"},
    ]