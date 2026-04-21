from __future__ import annotations

from typing import Any

from supabase import Client, create_client

from core.config import settings


class SupabaseStorageClient:
    def __init__(self) -> None:
        self.client: Client | None = None
        if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
            self.client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY,
            )

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def upload_bytes(
        self,
        path: str,
        content: bytes,
        content_type: str = "application/octet-stream",
    ) -> bool:
        if not self.client:
            return False

        try:
            bucket = self.client.storage.from_(settings.SUPABASE_BUCKET)
            bucket.upload(
                path,
                content,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            return True
        except Exception:
            return False

    def download_bytes(self, path: str) -> bytes | None:
        if not self.client:
            return None

        try:
            bucket = self.client.storage.from_(settings.SUPABASE_BUCKET)
            data: Any = bucket.download(path)
            if isinstance(data, bytes):
                return data
            return None
        except Exception:
            return None

    def remove(self, paths: list[str]) -> bool:
        if not self.client or not paths:
            return False

        try:
            bucket = self.client.storage.from_(settings.SUPABASE_BUCKET)
            bucket.remove(paths)
            return True
        except Exception:
            return False


supabase_storage = SupabaseStorageClient()
