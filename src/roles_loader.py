import pandas as pd
from . import config

def load_roles():
    """Load roles from the Excel file defined in .env."""
    df = pd.read_excel(config.ROLES_EXCEL)
    # we expect at least a column named 'Role'
    roles = df["Role"].dropna().tolist()
    return roles
