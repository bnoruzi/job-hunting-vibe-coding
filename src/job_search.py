import requests
from urllib.parse import quote
from . import config

def search_jobs_for_role(role: str):
    """Search SerpAPI for a given role and return a list of results."""
    query = f"{role} in {config.LOCATION} site:linkedin.com/jobs"
    url = (
        "https://serpapi.com/search.json"
        f"?engine=google&q={quote(query)}&api_key={config.SERPAPI_KEY}"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in data.get("organic_results", []):
        results.append({
            "title": item.get("title"),
            "link": item.get("link"),
            "source": "linkedin"
        })
    return results
