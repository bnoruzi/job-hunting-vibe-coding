import os
from typing import Dict, Any

from dotenv import load_dotenv

load_dotenv()  # load variables from .env


def _get_bool(env_name: str, default: bool) -> bool:
    value = os.getenv(env_name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Job_Finder")
GOOGLE_SHEET_TAB = os.getenv("GOOGLE_SHEET_TAB", "jobs")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
ROLES_EXCEL = os.getenv("ROLES_EXCEL", "data/Canada_IT_Roles_List.xlsx")
LOCATION = os.getenv("LOCATION", "Canada")
MAX_RESULTS_PER_ROLE = int(os.getenv("MAX_RESULTS_PER_ROLE", "8"))
DEFAULT_PROVIDER_LIMIT = int(os.getenv("DEFAULT_PROVIDER_LIMIT", "10"))
PROVIDER_REQUEST_TIMEOUT = float(os.getenv("PROVIDER_REQUEST_TIMEOUT", "10"))

PROVIDER_SETTINGS: Dict[str, Dict[str, Any]] = {
    "serpapi_linkedin": {
        "enabled": _get_bool("PROVIDER_SERPAPI_LINKEDIN_ENABLED", True),
        "api_key": os.getenv("PROVIDER_SERPAPI_LINKEDIN_API_KEY", SERPAPI_KEY),
        "result_limit": int(os.getenv("PROVIDER_SERPAPI_LINKEDIN_LIMIT", str(DEFAULT_PROVIDER_LIMIT))),
        "module": "providers.serpapi_linkedin",
        "label": os.getenv("PROVIDER_SERPAPI_LINKEDIN_LABEL", "LinkedIn (SerpAPI)"),
    },
    "serpapi_indeed": {
        "enabled": _get_bool("PROVIDER_SERPAPI_INDEED_ENABLED", True),
        "api_key": os.getenv("PROVIDER_SERPAPI_INDEED_API_KEY", SERPAPI_KEY),
        "result_limit": int(os.getenv("PROVIDER_SERPAPI_INDEED_LIMIT", str(DEFAULT_PROVIDER_LIMIT))),
        "module": "providers.serpapi_indeed",
        "label": os.getenv("PROVIDER_SERPAPI_INDEED_LABEL", "Indeed (SerpAPI)"),
    },
}
