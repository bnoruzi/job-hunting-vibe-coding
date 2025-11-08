import os
import requests
from dotenv import load_dotenv

load_dotenv()  # load variables from .env

api_key = os.getenv("SERPAPI_KEY")
if not api_key:
    raise ValueError("SERPAPI_KEY is missing in .env")

query = "technical support specialist jobs in Canada site:linkedin.com/jobs"

url = (
    "https://serpapi.com/search.json"
    f"?engine=google&q={query}&api_key={api_key}"
)

resp = requests.get(url)
resp.raise_for_status()  # will error if key is bad or request failed

data = resp.json()

for item in data.get("organic_results", [])[:5]:
    print(item.get("title"), "->", item.get("link"))
