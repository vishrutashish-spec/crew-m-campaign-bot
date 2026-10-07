import os

CT_ACCOUNT_ID = os.getenv("CT_ACCOUNT_ID", "")
CT_PASSCODE = os.getenv("CT_PASSCODE", "")
CT_REGION = os.getenv("CT_REGION", "in1")
CT_BASE_URL = f"https://{CT_REGION}.api.clevertap.com/1/"

CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")

N_PERSONAS = 8
RANDOM_SEED = 42
