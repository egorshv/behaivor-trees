from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "BT_DATABASE_URL",
            f"sqlite:///{Path(__file__).resolve().parents[1] / 'data' / 'behavior_trees.db'}",
        )
    )
    cors_origins: list[str] = field(
        default_factory=lambda: os.getenv(
            "BT_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
    )


def get_settings() -> Settings:
    return Settings()

