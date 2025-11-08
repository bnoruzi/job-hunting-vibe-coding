import gspread
from google.oauth2.service_account import Credentials
from . import config

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def get_sheet():
    """Authorize with Google and return the worksheet we want to use."""
    creds = Credentials.from_service_account_file(
        config.GOOGLE_SERVICE_ACCOUNT_JSON,
        scopes=SCOPES
    )
    client = gspread.authorize(creds)
    sheet = client.open(config.GOOGLE_SHEET_NAME).worksheet(config.GOOGLE_SHEET_TAB)
    return sheet
