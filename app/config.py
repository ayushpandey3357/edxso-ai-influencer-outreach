import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env if present
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Config:
    """System configuration settings loaded from environment variables."""

    # API Keys
    YOUTUBE_API_KEY: str = os.getenv("YOUTUBE_API_KEY", "").strip()
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "").strip()
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto").strip().lower()

    # Filtering Criteria (Configurable)
    MIN_SUBSCRIBERS: int = int(os.getenv("MIN_SUBSCRIBERS", "5000"))
    MAX_SUBSCRIBERS: int = int(os.getenv("MAX_SUBSCRIBERS", "100000"))
    MIN_ENGAGEMENT_RATE: float = float(os.getenv("MIN_ENGAGEMENT_RATE", "1.0"))

    # Pipeline Settings
    TARGET_DISCOVERY_COUNT: int = int(os.getenv("TARGET_DISCOVERY_COUNT", "60"))
    RECENT_VIDEO_COUNT: int = int(os.getenv("RECENT_VIDEO_COUNT", "5"))

    # Safety Controls
    SIMULATE_SEND: bool = os.getenv("SIMULATE_SEND", "true").lower() in ("true", "1", "yes")

    # Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = BASE_DIR / os.getenv("DB_PATH", "data/outreach.db")

    @classmethod
    def validate_youtube_key(cls) -> bool:
        """Returns True if YouTube API key is present."""
        return bool(cls.YOUTUBE_API_KEY and cls.YOUTUBE_API_KEY != "your_youtube_api_key_here")

    @classmethod
    def validate_llm_key(cls) -> bool:
        """Returns True if either OpenAI or Gemini API key is present."""
        has_openai = bool(cls.OPENAI_API_KEY and cls.OPENAI_API_KEY != "your_openai_api_key_here")
        has_gemini = bool(cls.GEMINI_API_KEY and cls.GEMINI_API_KEY != "your_gemini_api_key_here")
        return has_openai or has_gemini
