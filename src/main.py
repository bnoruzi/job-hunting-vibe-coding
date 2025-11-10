from datetime import datetime
from typing import Dict, List, Tuple

from .google_sheet import get_sheet
from .roles_loader import load_roles
from .job_search import search_jobs_for_role
from . import config

BASE_HEADER = ["Fetched At (UTC)", "Role", "Job Title", "Source", "Link"]

_DATE_POSTED_OPTIONS: List[Tuple[str, str, str]] = [
    ("1", "any", "Any time"),
    ("2", "past_24_hours", "Past 24 hours"),
    ("3", "past_week", "Past week"),
    ("4", "past_month", "Past month"),
]

_JOB_TYPE_OPTIONS: List[Tuple[str, str, str]] = [
    ("1", "any", "Any"),
    ("2", "full-time", "Full-time"),
    ("3", "part-time", "Part-time"),
    ("4", "contract", "Contract"),
    ("5", "internship", "Internship"),
]


def _header_to_key(header: str) -> str:
    return header.lower().replace(" ", "_")


def _key_to_header(key: str) -> str:
    return key.replace("_", " ").title()


def _prepare_header(existing_header: List[str]) -> List[str]:
    if not existing_header:
        return BASE_HEADER.copy()
    return list(existing_header)


def _extract_metadata_keys(header: List[str]) -> List[str]:
    metadata_keys: List[str] = []
    for column in header:
        if column not in BASE_HEADER:
            metadata_keys.append(_header_to_key(column))
    return metadata_keys


def _ensure_header(sheet, header: List[str]):
    sheet.update("A1", [header])


def _prompt_locations() -> List[str]:
    default_location = config.LOCATION
    prompt = (
        "Enter locations separated by commas "
        f"(press Enter for default: {default_location}): "
    )
    raw_locations = input(prompt).strip()
    if not raw_locations:
        return [default_location]
    return [part.strip() for part in raw_locations.split(",") if part.strip()]


def _prompt_choice(options: List[Tuple[str, str, str]], title: str, default_key: str) -> str:
    print(title)
    for key, value, label in options:
        default_marker = " (default)" if key == default_key else ""
        print(f"  {key}. {label}{default_marker}")
    choice = input("Select an option: ").strip() or default_key
    valid_keys = {key for key, _, _ in options}
    if choice not in valid_keys:
        print(f"Invalid selection '{choice}', using default option.")
        choice = default_key
    mapping = {key: value for key, value, _ in options}
    return mapping[choice]


def _collect_filters() -> Tuple[List[str], Dict[str, str]]:
    print("Configure dynamic filters (press Enter to accept defaults).")
    locations = _prompt_locations()
    date_choice = _prompt_choice(
        _DATE_POSTED_OPTIONS, "Date posted filter:", default_key="1"
    )
    job_type_choice = _prompt_choice(
        _JOB_TYPE_OPTIONS, "Job type filter:", default_key="1"
    )
    keywords = input(
        "Additional keywords to include in every search (optional): "
    ).strip()

    filters: Dict[str, str] = {}
    if date_choice != "any":
        filters["date_posted"] = date_choice
    if job_type_choice != "any":
        filters["job_type"] = job_type_choice
    if keywords:
        filters["keywords"] = keywords

    print("\nUsing filters:")
    print(f"  Locations: {', '.join(locations)}")
    print(
        "  Date posted: "
        + next(
            label
            for _, value, label in _DATE_POSTED_OPTIONS
            if value == date_choice
        )
    )
    print(
        "  Job type: "
        + next(label for _, value, label in _JOB_TYPE_OPTIONS if value == job_type_choice)
    )
    if keywords:
        print(f"  Additional keywords: {keywords}")

    return locations, filters


def main():
    sheet = get_sheet()
    roles = load_roles()
    locations, filters = _collect_filters()

    existing = sheet.get_all_values()
    header = _prepare_header(existing[0] if existing else [])
    metadata_keys = _extract_metadata_keys(header)

    if not existing:
        _ensure_header(sheet, header)

    existing_links = set()
    if existing:
        link_idx = header.index("Link") if "Link" in header else -1
        if link_idx >= 0:
            for row in existing[1:]:
                if len(row) > link_idx and row[link_idx]:
                    existing_links.add(row[link_idx])

    for role in roles:
        results = search_jobs_for_role(role, locations, filters)

        # discover new metadata keys before writing rows
        updated_header = False
        for item in results:
            metadata = item.get("metadata", {})
            for key in metadata:
                if key not in metadata_keys:
                    metadata_keys.append(key)
                    header.append(_key_to_header(key))
                    updated_header = True
        if updated_header:
            _ensure_header(sheet, header)

        added = 0
        for item in results:
            if added >= config.MAX_RESULTS_PER_ROLE:
                break
            link = item.get("link")
            if not link or link in existing_links:
                continue

            metadata = item.get("metadata", {})
            row = [
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                role,
                item.get("title"),
                item.get("source"),
                link,
            ]
            for key in metadata_keys:
                row.append(metadata.get(key, ""))

            sheet.append_row(row)
            existing_links.add(link)
            added += 1

        print(f"Processed role: {role} (added {added} jobs)")


if __name__ == "__main__":
    main()
