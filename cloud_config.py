"""Environment-only configuration for CraftLife's optional Supabase integration."""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Source mode: .env beside cloud_config.py.
# PyInstaller mode: .env remains external beside CraftLife.exe, never inside _MEIPASS.
PROJECT_ROOT = (Path(sys.executable).resolve().parent
                if getattr(sys, "frozen", False)
                else Path(__file__).resolve().parent)
ENV_PATH = PROJECT_ROOT / ".env"

try:
    from dotenv import load_dotenv
    # Always load the .env beside cloud_config.py, independent of terminal cwd.
    load_dotenv(dotenv_path=ENV_PATH, override=False)
except ImportError:
    pass


@dataclass(frozen=True)
class CloudConfig:
    url: str
    publishable_key: str
    enabled: bool = True
    sync_interval_seconds: int = 60
    profile_bucket: str = "profile-photos"
    gallery_bucket: str = "love-space-photos"
    chat_bucket: str = "chat-attachments"

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.url and self.publishable_key)


def load_cloud_config() -> CloudConfig:
    enabled = os.getenv("CRAFTLIFE_CLOUD_ENABLED", "true").strip().lower() not in {
        "0", "false", "no", "off"
    }
    try:
        interval = max(15, int(os.getenv("CRAFTLIFE_SYNC_INTERVAL_SECONDS", "60")))
    except ValueError:
        interval = 60
    return CloudConfig(
        url=(os.getenv("SUPABASE_URL", "").strip()
             or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "").strip()).rstrip("/"),
        publishable_key=(os.getenv("SUPABASE_PUBLISHABLE_KEY", "").strip()
                         or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "").strip()
                         or os.getenv("SUPABASE_ANON_KEY", "").strip()),
        enabled=enabled,
        sync_interval_seconds=interval,
    )
