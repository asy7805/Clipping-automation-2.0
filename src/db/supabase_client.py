# src/db/supabase_client.py
import os
from typing import Any, Dict, Optional
from supabase import create_client, Client  # pip: supabase>=2
from dataclasses import dataclass


REQUIRED_ENV = ["SUPABASE_URL", "SUPABASE_ANON_KEY"]  # service role only on server
# If you are running privileged scripts (server-only), set USE_SERVICE_ROLE=true in env.
if os.getenv("USE_SERVICE_ROLE", "false").lower() == "true":
    REQUIRED_ENV.append("SUPABASE_SERVICE_ROLE_KEY")


@dataclass(frozen=True)
class SupabaseConfig:
    url: str
    key: str


_client: Optional[Client] = None  # lazy singleton


def _load_config() -> SupabaseConfig:
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    url = os.getenv("SUPABASE_URL", "").strip()
    # Prefer service role when explicitly enabled (server env only).
    key = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY").strip()
        if os.getenv("USE_SERVICE_ROLE", "false").lower() == "true"
        else os.getenv("SUPABASE_ANON_KEY", "").strip()
    )

    if not url or not key:
        raise RuntimeError("Supabase URL or API key is empty. Check your .env.")

    return SupabaseConfig(url=url, key=key)


def get_client() -> Client:
    """Return a process-wide Supabase client singleton."""
    global _client
    if _client is None:
        cfg = _load_config()
        _client = create_client(cfg.url, cfg.key)
    return _client


# ---------- Convenience helpers (optional but handy) ----------

def insert_row(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a single row and return the inserted row.
    Usage: insert_row("streams", {...})
    """
    sb = get_client()
    resp = sb.table(table).insert(data).select("*").single().execute()
    if resp.data is None:
        raise RuntimeError(f"Insert returned no data: {resp}")
    return resp.data


def fetch_one(table: str, **eq_filters) -> Optional[Dict[str, Any]]:
    """
    Simple equality filter fetch. Returns first row or None.
    Usage: fetch_one("streams", id="...", user_id="...")
    """
    sb = get_client()
    q = sb.table(table).select("*")
    for k, v in eq_filters.items():
        q = q.eq(k, v)
    resp = q.limit(1).execute()
    if not resp.data:
        return None
    return resp.data[0]


def upload_bytes(bucket: str, path: str, blob: bytes, upsert: bool = True) -> str:
    """
    Upload raw bytes to Storage and return the path.
    NOTE: URL generation depends on your bucket's public/private setting.
    """
    sb = get_client()
    sb.storage.from_(bucket).upload(path, blob, {"upsert": upsert})
    return path


def get_public_url(bucket: str, path: str) -> str:
    """
    If the bucket is public, returns a direct URL. If private, you'll need a signed URL instead.
    """
    sb = get_client()
    return sb.storage.from_(bucket).get_public_url(path)