from datetime import datetime
from .google_sheet import get_sheet          # relative import: look in the same package
from .roles_loader import load_roles         # relative import
from .job_search import search_jobs_for_role # relative import
from . import config                         # relative import


def main():
    sheet = get_sheet()
    roles = load_roles()

    # read existing rows to avoid duplicates
    existing = sheet.get_all_values()
    existing_links = set()
    if existing:
        header = existing[0]
        if "Link" in header:
            link_idx = header.index("Link")
            for row in existing[1:]:
                if len(row) > link_idx:
                    existing_links.add(row[link_idx])

    # if sheet is empty, write header
    if not existing:
        sheet.append_row(["Fetched At (UTC)", "Role", "Job Title", "Source", "Link"])

    for role in roles:
        results = search_jobs_for_role(role)
        added = 0
        for item in results:
            if added >= config.MAX_RESULTS_PER_ROLE:
                break
            link = item["link"]
            if not link:
                continue
            if link in existing_links:
                continue
            sheet.append_row([
                datetime.utcnow().isoformat(timespec="seconds") + "Z",
                role,
                item["title"],
                item["source"],
                link
            ])
            existing_links.add(link)
            added += 1
        print(f"Processed role: {role} (added {added} jobs)")

if __name__ == "__main__":
    main()
