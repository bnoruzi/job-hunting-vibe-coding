import argparse
import time
from datetime import datetime
from typing import Dict, List, Tuple

from .google_sheet import get_sheet
from .roles_loader import load_roles
from .job_search import search_jobs_for_role
from .storage.sheets_repository import SheetsRepository
from . import config
from .ai import EnrichmentError, enrich_job

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


def _collect_filters(interactive: bool) -> Tuple[List[str], Dict[str, str]]:
    if not interactive:
        locations = [config.LOCATION]
        filters: Dict[str, str] = {}
        print("Using default filters (non-interactive mode).")
        print(f"  Locations: {', '.join(locations)}")
        print("  Date posted: Any time")
        print("  Job type: Any")
        return locations, filters

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


def _run_once(locations: List[str], filters: Dict[str, str]) -> None:
    sheet = get_sheet()
    repository = SheetsRepository(sheet)
    roles = load_roles()

    for role in roles:
        results = search_jobs_for_role(role, locations, filters)

        added = 0
        for item in results:
            if added >= config.MAX_RESULTS_PER_ROLE:
                break

            link = item.get("link")
            if not link:
                continue

            enrichment_payload = item.get("enrichment")
            if config.AI_ENRICHMENT_ENABLED and not enrichment_payload:
                try:
                    enrichment_payload = enrich_job(item)
                except EnrichmentError as exc:
                    print(f"[WARN] Failed to enrich job {link}: {exc}")
                else:
                    if enrichment_payload:
                        item["enrichment"] = enrichment_payload

            was_created = repository.upsert_job(
                fetched_at=datetime.utcnow().isoformat(timespec="seconds") + "Z",
                role=role,
                title=item.get("title"),
                source=item.get("source"),
                link=link,
                metadata=item.get("metadata", {}),
                enrichment=item.get("enrichment"),
            )

            if was_created:
                added += 1

        print(f"Processed role: {role} (added {added} jobs)")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch job listings and persist them.")
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run without prompts, using default configuration values.",
    )
    parser.add_argument(
        "--schedule-minutes",
        type=int,
        help="Run continuously, fetching jobs every N minutes.",
    )
    return parser.parse_args()


def main():
    args = _parse_args()
    schedule_minutes = args.schedule_minutes
    non_interactive = args.non_interactive or schedule_minutes is not None

    locations, filters = _collect_filters(interactive=not non_interactive)

    if schedule_minutes is not None:
        interval = max(schedule_minutes, 1)
        print(
            f"Starting periodic fetch every {interval} minute(s). Press Ctrl+C to exit."
        )
        try:
            while True:
                _run_once(locations, filters)
                print(f"Sleeping for {interval} minute(s)...")
                time.sleep(interval * 60)
        except KeyboardInterrupt:
            print("Stopping periodic fetch.")
        return

    _run_once(locations, filters)


if __name__ == "__main__":
    main()
