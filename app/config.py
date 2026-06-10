import os

def _b(v): return str(v).lower() in ("1", "true", "yes", "on")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
USE_VERTEX     = _b(os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "0"))
GCP_PROJECT    = os.getenv("GOOGLE_CLOUD_PROJECT", "")
GCP_LOCATION   = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
EE_PROJECT     = os.getenv("EE_PROJECT", "")
HANSEN_ASSET   = os.getenv("HANSEN_ASSET", "UMD/hansen/global_forest_change_2023_v1_11")
CUTOFF_YEAR    = int(os.getenv("DEFORESTATION_CUTOFF_YEAR", "2020"))
GFW_API_KEY    = os.getenv("GFW_API_KEY", "")
GFW_VERSION    = os.getenv("GFW_VERSION", "v1.11")
LOSS_THRESHOLD_HA = float(os.getenv("LOSS_THRESHOLD_HA", "0.1"))
ALERTS_THRESHOLD  = int(os.getenv("ALERTS_THRESHOLD", "3"))
GCS_BUCKET     = os.getenv("GCS_BUCKET", "")
DATA_DIR       = os.getenv("DATA_DIR", "./_data")
# --- Login con Google ---
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
SESSION_SECRET         = os.getenv("SESSION_SECRET", "dev-insecure-change-me")
PUBLIC_BASE_URL        = os.getenv("PUBLIC_BASE_URL", "https://origen-711831043664.us-central1.run.app")

def gemini_ready(): return bool(GEMINI_API_KEY or USE_VERTEX)
def auth_ready():   return bool(GOOGLE_OAUTH_CLIENT_ID)
