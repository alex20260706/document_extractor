"""Runtime configuration for the document-extraction service."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


def _root_env_file() -> Path:
    """Locate the repository environment file during development.

    Returns:
        The repository ``.env`` path, or a working-directory fallback.
    """

    for directory in Path(__file__).resolve().parents:
        if (directory / "docker-compose.yml").is_file():
            return directory / ".env"
    return Path.cwd() / ".env"


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_env: str = "development"
    max_upload_mb: int = 10
    cors_origins: str = "http://localhost:4200"
    ocr_languages: str = "spa+eng"
    ocr_dpi: int = 300
    ocr_max_pages: int = 20
    ocr_max_pixels_per_page: int = 40_000_000
    tesseract_cmd: str | None = None
    # Hybrid extraction is the product default.
    # It still requires a complete
    # provider configuration before external requests can be made.
    llm_enabled: bool = True
    llm_base_url: str | None = None
    llm_api_key: SecretStr | None = None
    llm_model: str | None = None
    llm_timeout_seconds: float = 30.0
    llm_max_input_characters: int = 60_000
    llm_max_output_tokens: int = 2_500
    llm_strict_schema: bool = False

    model_config = SettingsConfigDict(
        env_file=_root_env_file(),
        extra="ignore",
    )

    @property
    def allowed_origins(self) -> list[str]:
        """Parse configured CORS origins.

        Returns:
            Non-empty origins with surrounding whitespace removed.
        """
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide runtime settings.

    Returns:
        The cached application settings.
    """
    return Settings()
