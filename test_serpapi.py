import os
import pytest
import requests
from dotenv import load_dotenv

load_dotenv()  # load variables from .env

api_key = os.getenv("SERPAPI_KEY")
if not api_key:
    pytest.skip("SERPAPI_KEY is missing in .env", allow_module_level=True)


def test_serpapi_fetch():
    query = "technical support specialist jobs in Canada site:linkedin.com/jobs"

    url = (
        "https://serpapi.com/search.json"
        f"?engine=google&q={query}&api_key={api_key}"
    )

    resp = requests.get(url)
    resp.raise_for_status()  # will error if key is bad or request failed

    data = resp.json()

    assert "organic_results" in data
