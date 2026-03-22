import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _get_setting(name: str, default=None):
    """Read config from env first, then Streamlit secrets (Cloud), then default."""
    env_val = os.getenv(name)
    if env_val is not None:
        return env_val

    try:
        import streamlit as st

        if name in st.secrets:
            return st.secrets[name]
    except Exception:
        # Not running inside Streamlit (or secrets unavailable).
        pass

    return default


def _as_bool(value, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() == "true"


def _as_int(value, default: int) -> int:
    if value is None or str(value).strip() == "":
        return default
    return int(value)


def _optional_int(name: str):
    raw = _get_setting(name, "")
    raw = str(raw).strip()
    if raw == "":
        return None
    return int(raw)


def _optional_csv(name: str):
    raw = _get_setting(name, "")
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]

    raw_str = str(raw).strip()
    if raw_str == "":
        return []
    return [item.strip() for item in raw_str.split(",") if item.strip()]


class Config:
    APP_NAME: str = "SIPMT"
    APP_VERSION: str = "1.0.0"
    DOCUMENT_CATEGORIES: list = [
        "Questionnaire",
        "Policies",
        "Instructions",
        "Forms",
        "Reports",
        "Monitoring",
    ]

    # Paths
    BASE_DIR: Path = BASE_DIR
    DATABASE_URL: str = str(_get_setting("DATABASE_URL", ""))
    DATABASE_PATH: str = str(_get_setting("DATABASE_PATH", str(BASE_DIR / "data" / "sipmt.db")))
    SQLITE_MIRROR_PATH: str = str(_get_setting("SQLITE_MIRROR_PATH", DATABASE_PATH))
    UPLOAD_FOLDER: str = str(_get_setting("UPLOAD_FOLDER", str(BASE_DIR / "uploads")))
    EXPORT_FOLDER: str = str(_get_setting("EXPORT_FOLDER", str(BASE_DIR / "exports")))
    TEMP_FOLDER: str = str(_get_setting("TEMP_FOLDER", str(BASE_DIR / "temp")))
    LOG_FILE: str = str(_get_setting("LOG_FILE", str(BASE_DIR / "logs" / "sipmt.log")))
    FORCE_POSTGRES: bool = _as_bool(_get_setting("FORCE_POSTGRES", "False"), default=False)
    FORCE_SQLITE: bool = _as_bool(_get_setting("FORCE_SQLITE", "False"), default=False)
    ENABLE_SQLITE_MIRROR_SYNC: bool = _as_bool(_get_setting("ENABLE_SQLITE_MIRROR_SYNC", "False"), default=False)

    # Application
    DEBUG: bool = _as_bool(_get_setting("DEBUG", "False"), default=False)
    SECRET_KEY: str = str(_get_setting("SECRET_KEY", "change-me-in-production"))

    # File handling
    MAX_FILE_SIZE: int = _as_int(_get_setting("MAX_FILE_SIZE", str(10 * 1024 * 1024)), 10 * 1024 * 1024)
    ALLOWED_EXTENSIONS: list = ["pdf", "docx", "doc", "xlsx", "xls"]
    STORE_FILES_IN_DB: bool = _as_bool(_get_setting("STORE_FILES_IN_DB", "False"), default=False)

    # OCR
    ENABLE_OCR: bool = _as_bool(_get_setting("ENABLE_OCR", "False"), default=False)
    OCR_LANGUAGE: str = str(_get_setting("OCR_LANGUAGE", "eng"))

    # NLP
    SPACY_MODEL: str = str(_get_setting("SPACY_MODEL", "en_core_web_sm"))

    # Matching
    FUZZY_MATCH_THRESHOLD: float = float(_get_setting("FUZZY_MATCH_THRESHOLD", "0.7"))
    CONFIDENCE_THRESHOLD: float = float(_get_setting("CONFIDENCE_THRESHOLD", "0.6"))

    # Geospatial
    ENABLE_GEOCODING: bool = _as_bool(_get_setting("ENABLE_GEOCODING", "True"), default=True)
    DEFAULT_MAP_CENTER: list = [44.0, 21.0]  # Serbia default
    DEFAULT_MAP_ZOOM: int = 7

    # Semantic Analysis provider
    SEMANTIC_LLM_PROVIDER: str = str(_get_setting("SEMANTIC_LLM_PROVIDER", "ollama")).lower()

    # Google Gemini
    GEMINI_API_KEY: str = str(_get_setting("GEMINI_API_KEY", ""))
    GEMINI_MODEL: str = str(_get_setting("GEMINI_MODEL", "gemini-2.0-flash"))
    GEMINI_FALLBACK_MODELS: list = _optional_csv("GEMINI_FALLBACK_MODELS")

    # Ollama (local)
    OLLAMA_BASE_URL: str = str(_get_setting("OLLAMA_BASE_URL", "http://localhost:11434"))
    OLLAMA_MODEL: str = str(_get_setting("OLLAMA_MODEL", "qwen2.5:14b-instruct"))
    OLLAMA_TIMEOUT_SEC: int = _as_int(_get_setting("OLLAMA_TIMEOUT_SEC", "300"), 300)
    OLLAMA_KEEP_ALIVE: str = str(_get_setting("OLLAMA_KEEP_ALIVE", "30m"))
    OLLAMA_NUM_CTX: int = _as_int(_get_setting("OLLAMA_NUM_CTX", "4096"), 4096)
    OLLAMA_NUM_THREAD = _optional_int("OLLAMA_NUM_THREAD")
    OLLAMA_NUM_GPU = _optional_int("OLLAMA_NUM_GPU")
    OLLAMA_NUM_BATCH = _optional_int("OLLAMA_NUM_BATCH")
    COMPLIANCE_STEP_TIMEOUT_SEC: int = _as_int(_get_setting("COMPLIANCE_STEP_TIMEOUT_SEC", "120"), 120)
    COMPLIANCE_TOKENIZE_CHAR_LIMIT: int = _as_int(_get_setting("COMPLIANCE_TOKENIZE_CHAR_LIMIT", "250000"), 250000)

    ENABLE_SEMANTIC_ANALYSIS: bool = _as_bool(_get_setting("ENABLE_SEMANTIC_ANALYSIS", "False"), default=False)
    REFERENCE_TEMPLATES_DIR: str = str(
        _get_setting("REFERENCE_TEMPLATES_DIR", str(BASE_DIR / "reference_templates"))
    )

    # Logging
    LOG_LEVEL: str = str(_get_setting("LOG_LEVEL", "INFO"))

    @classmethod
    def ensure_directories(cls) -> None:
        """Create all required runtime directories."""
        for path in [
            cls.UPLOAD_FOLDER,
            cls.EXPORT_FOLDER,
            cls.TEMP_FOLDER,
            Path(cls.DATABASE_PATH).parent,
            Path(cls.LOG_FILE).parent,
        ]:
            Path(path).mkdir(parents=True, exist_ok=True)
