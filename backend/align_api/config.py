"""Environment-derived backend settings."""

from dataclasses import dataclass
from os import environ
from typing import Mapping


@dataclass(frozen=True)
class Settings:
    app_name: str
    environment: str
    database_url: str | None

    @property
    def database_configured(self) -> bool:
        return bool(self.database_url)


def load_settings(values: Mapping[str, str] | None = None) -> Settings:
    """Load non-secret settings; no database connection is attempted here."""
    source = environ if values is None else values
    return Settings(
        app_name=source.get("ALIGN_APP_NAME", "Align API"),
        environment=source.get("ALIGN_ENV", "development"),
        database_url=source.get("ALIGN_DATABASE_URL") or None,
    )
