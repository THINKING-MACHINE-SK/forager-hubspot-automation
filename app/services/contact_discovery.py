def filter_contacts_by_title(
    contacts: list[dict],
    allowed_titles: list[str],
) -> list[dict]:
    allowed = {title.strip().casefold() for title in allowed_titles}

    return [
        contact
        for contact in contacts
        if (contact.get("job_title") or "").strip().casefold() in allowed
    ]