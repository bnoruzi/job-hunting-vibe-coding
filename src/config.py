import os
from dotenv import load_dotenv

load_dotenv()  # load variables from .env

SERPAPI_KEY = os.getenv("SERPAPI_KEY")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Job_Finder")
GOOGLE_SHEET_TAB = os.getenv("GOOGLE_SHEET_TAB", "jobs")
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "service_account.json")
ROLES_EXCEL = os.getenv("ROLES_EXCEL", "data/Canada_IT_Roles_List.xlsx")
LOCATION = os.getenv("LOCATION", "Canada")
MAX_RESULTS_PER_ROLE = int(os.getenv("MAX_RESULTS_PER_ROLE", "8"))
