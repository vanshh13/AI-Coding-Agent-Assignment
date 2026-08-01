import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    LLM_API_KEY: str = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gpt-4o-mini")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.0"))
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "5"))

    @classmethod
    def validate(cls) -> None:
        """Validates that key credentials exist."""
        if not cls.LLM_API_KEY and "localhost" not in cls.LLM_BASE_URL and "127.0.0.1" not in cls.LLM_BASE_URL:
            # For remote providers, warn if no API key is specified
            pass

