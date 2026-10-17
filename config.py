import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_MODEL_NAME = "gemini-3.6-flash"


def load_dotenv_file(path=BASE_DIR / ".env"):
    """Small .env loader so the app does not require python-dotenv."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def get_gemini_api_key():
    load_dotenv_file()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY was not found. Add it to .env before running UDAY.")
    return api_key


def validate_deployment_environment():
    """Fail early on hosted deployments misconfigured with ephemeral storage/secrets."""
    load_dotenv_file()
    if os.getenv("UDAY_REQUIRE_DATABASE") == "1" and not os.getenv("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is required for this deployment. Configure persistent PostgreSQL.")
    secret = os.getenv("JWT_SECRET_KEY", "")
    if os.getenv("UDAY_REQUIRE_DATABASE") == "1" and len(secret) < 32:
        raise RuntimeError("JWT_SECRET_KEY must be at least 32 characters in deployment.")
    if os.getenv("UDAY_REQUIRE_DATABASE") == "1" and not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is required for this deployment.")


def get_model_name():
    load_dotenv_file()
    return os.getenv("GEMINI_MODEL", DEFAULT_MODEL_NAME)
