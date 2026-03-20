import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent


def _optional_int(name: str):
    raw = os.getenv(name, "").strip()
    if raw == "":
        return None
    return int(raw)


def _optional_csv(name: str):
    raw = os.getenv(name, "").strip()
    if raw == "":
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


class Config:
    APP_NAME: str = "INCLUSCAPE"
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
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "data" / "incluscape.db"))
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", str(BASE_DIR / "uploads"))
    EXPORT_FOLDER: str = os.getenv("EXPORT_FOLDER", str(BASE_DIR / "exports"))
    TEMP_FOLDER: str = os.getenv("TEMP_FOLDER", str(BASE_DIR / "temp"))
    LOG_FILE: str = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "incluscape.log"))

    # Application
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production")

    # File handling
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", str(10 * 1024 * 1024)))
    ALLOWED_EXTENSIONS: list = ["pdf", "docx", "doc", "xlsx", "xls"]

    # OCR
    ENABLE_OCR: bool = os.getenv("ENABLE_OCR", "False").lower() == "true"
    OCR_LANGUAGE: str = os.getenv("OCR_LANGUAGE", "eng")

    # NLP
    SPACY_MODEL: str = os.getenv("SPACY_MODEL", "en_core_web_sm")

    # Matching
    FUZZY_MATCH_THRESHOLD: float = float(os.getenv("FUZZY_MATCH_THRESHOLD", "0.7"))
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))

    # Geospatial
    ENABLE_GEOCODING: bool = os.getenv("ENABLE_GEOCODING", "False").lower() == "true"
    DEFAULT_MAP_CENTER: list = [44.0, 21.0]  # Serbia default
    DEFAULT_MAP_ZOOM: int = 7

    # Semantic Analysis provider
    SEMANTIC_LLM_PROVIDER: str = os.getenv("SEMANTIC_LLM_PROVIDER", "gemini").lower()

    # Google Gemini
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    GEMINI_FALLBACK_MODELS: list = _optional_csv("GEMINI_FALLBACK_MODELS")

    # Ollama (local)
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen2.5:14b-instruct")
    OLLAMA_TIMEOUT_SEC: int = int(os.getenv("OLLAMA_TIMEOUT_SEC", "300"))
    OLLAMA_KEEP_ALIVE: str = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
    OLLAMA_NUM_CTX: int = int(os.getenv("OLLAMA_NUM_CTX", "4096"))
    OLLAMA_NUM_THREAD = _optional_int("OLLAMA_NUM_THREAD")
    OLLAMA_NUM_GPU = _optional_int("OLLAMA_NUM_GPU")
    OLLAMA_NUM_BATCH = _optional_int("OLLAMA_NUM_BATCH")
    COMPLIANCE_STEP_TIMEOUT_SEC: int = int(os.getenv("COMPLIANCE_STEP_TIMEOUT_SEC", "120"))
    COMPLIANCE_TOKENIZE_CHAR_LIMIT: int = int(os.getenv("COMPLIANCE_TOKENIZE_CHAR_LIMIT", "250000"))

    ENABLE_SEMANTIC_ANALYSIS: bool = os.getenv("ENABLE_SEMANTIC_ANALYSIS", "False").lower() == "true"
    REFERENCE_TEMPLATES_DIR: str = os.getenv(
        "REFERENCE_TEMPLATES_DIR", str(BASE_DIR / "reference_templates")
    )

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

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
