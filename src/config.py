import json
import os
from typing import Any, Dict

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


# ---------------------------------------------------------------------------
# AI enrichment configuration
# ---------------------------------------------------------------------------

AI_ENRICHMENT_ENABLED = _get_bool("AI_ENRICHMENT_ENABLED", False)
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
AI_MODEL = os.getenv("AI_MODEL", "gpt-4o-mini")
AI_API_KEY = os.getenv("AI_API_KEY")
AI_ORG = os.getenv("AI_ORG")
AI_BASE_URL = os.getenv("AI_BASE_URL", "https://api.openai.com/v1")
AI_COMPLETIONS_URL = os.getenv("AI_COMPLETIONS_URL")
AI_TEMPERATURE = float(os.getenv("AI_TEMPERATURE", "0.2"))
AI_TIMEOUT = float(os.getenv("AI_TIMEOUT", "30"))
AI_MAX_RETRIES = int(os.getenv("AI_MAX_RETRIES", "3"))
AI_RETRY_BACKOFF_SECONDS = float(os.getenv("AI_RETRY_BACKOFF_SECONDS", "2"))
AI_RESPONSE_FORMAT_JSON = _get_bool("AI_RESPONSE_FORMAT_JSON", True)
AI_ENRICHMENT_ALERTS_ENABLED = _get_bool("AI_ENRICHMENT_ALERTS_ENABLED", False)
AI_ENRICHMENT_ALERT_THRESHOLD = float(
    os.getenv("AI_ENRICHMENT_ALERT_THRESHOLD", "0")
)

_DEFAULT_SYSTEM_PROMPT = (
    "You are an expert talent researcher helping a job-seeking candidate. "
    "Return concise JSON with insights tailored to the candidate profile."
)
_DEFAULT_USER_PROMPT = (
    "You are supporting a candidate with the following profile: {candidate_profile}.\n\n"
    "Evaluate this job posting and respond in strict JSON with keys 'fit_score', "
    "'summary', and 'outreach_angle'.\n\n"
    "Job Title: {job_title}\n"
    "Company: {company}\n"
    "Location: {location}\n"
    "Link: {link}\n"
    "Description: {description}\n\n"
    "Return fit_score as a number from 0-100 summarizing overall fit, summary as a "
    "two-sentence overview referencing skills and requirements, and outreach_angle "
    "with a suggestion for how the candidate should position themselves when "
    "reaching out."
)
_DEFAULT_CANDIDATE_PROFILE = (
    "Senior full-stack software engineer specializing in Python, cloud platforms, "
    "and AI-driven products. Interested in impactful, collaborative teams."
)


def _load_prompt_template(env_name: str, default: str) -> str:
    raw = os.getenv(env_name)
    if not raw:
        return default
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return raw
        return str(data.get("template", default))
    return raw


AI_PROMPT_TEMPLATES: Dict[str, str] = {
    "system": _load_prompt_template("AI_SYSTEM_PROMPT", _DEFAULT_SYSTEM_PROMPT),
    "user": _load_prompt_template("AI_USER_PROMPT", _DEFAULT_USER_PROMPT),
    "candidate_profile": os.getenv(
        "AI_CANDIDATE_PROFILE", _DEFAULT_CANDIDATE_PROFILE
    ),
}
