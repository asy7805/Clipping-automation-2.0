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
_admin_client: Optional[Client] = None  # admin client with service role key


def _load_config() -> SupabaseConfig:
    missing = [k for k in REQUIRED_ENV if not os.getenv(k)]
    if missing:
        raise RuntimeError(f"Missing required env vars: {', '.join(missing)}")

    url = os.getenv("SUPABASE_URL") or ""
    url = url.strip() if url else ""
    
    # Prefer service role when explicitly enabled (server env only).
    if os.getenv("USE_SERVICE_ROLE", "false").lower() == "true":
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
        key = service_key.strip() if service_key else ""
    else:
        anon_key = os.getenv("SUPABASE_ANON_KEY") or ""
        key = anon_key.strip() if anon_key else ""

    if not url or not key:
        raise RuntimeError("Supabase URL or API key is empty. Check your .env.")

    return SupabaseConfig(url=url, key=key)


def get_client() -> Client:
    """Return a process-wide Supabase client singleton."""
    global _client
    if _client is None:
        cfg = _load_config()
        try:
            _client = create_client(cfg.url, cfg.key)
        except Exception as e:
            error_msg = str(e)
            if "nodename" in error_msg.lower() or "servname" in error_msg.lower():
                raise RuntimeError(
                    f"DNS resolution failed for Supabase URL: {cfg.url}. "
                    f"Check your network connection and SUPABASE_URL environment variable. "
                    f"Original error: {error_msg}"
                )
            raise
    return _client

def get_admin_client() -> Client:
    """
    Return a Supabase client with service role key (bypasses RLS).
    Use this for admin operations that need to access protected tables.
    """
    global _admin_client
    if _admin_client is None:
        url = os.getenv("SUPABASE_URL") or ""
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or ""
        
        # Strip whitespace if values exist
        url = url.strip() if url else ""
        service_key = service_key.strip() if service_key else ""
        
        if not url or not service_key:
            raise RuntimeError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY required for admin client. "
                "Admin operations need service role key to bypass RLS. "
                f"URL: {'set' if url else 'missing'}, Service Key: {'set' if service_key else 'missing'}"
            )
        
        try:
            _admin_client = create_client(url, service_key)
        except Exception as e:
            error_msg = str(e)
            if "nodename" in error_msg.lower() or "servname" in error_msg.lower():
                raise RuntimeError(
                    f"DNS resolution failed for Supabase URL: {url}. "
                    f"Check your network connection and SUPABASE_URL environment variable. "
                    f"Original error: {error_msg}"
                )
            raise
    return _admin_client


# ---------- Convenience helpers (optional but handy) ----------

def insert_row(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Insert a single row and return the inserted row.
    Usage: insert_row("streams", {...})
    """
    sb = get_client()
    resp = sb.table(table).insert(data).execute()
    if not resp.data:
        raise RuntimeError(f"Insert returned no data: {resp}")
    return resp.data[0]


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
    file_options = {"upsert": str(upsert).lower()}
    sb.storage.from_(bucket).upload(path, blob, file_options)
    return path


def get_public_url(bucket: str, path: str) -> str:
    """
    If the bucket is public, returns a direct URL. If private, you'll need a signed URL instead.
    """
    try:
        sb = get_client()
        # Construct public URL manually to avoid DNS issues
        # Format: https://<project-ref>.supabase.co/storage/v1/object/public/<bucket>/<path>
        supabase_url = os.getenv("SUPABASE_URL", "").rstrip('/')
        if not supabase_url:
            raise RuntimeError("SUPABASE_URL not set")
        
        # Remove trailing slash and construct public URL
        public_url = f"{supabase_url}/storage/v1/object/public/{bucket}/{path}"
        return public_url
    except Exception as e:
        # Fallback to Supabase client method if manual construction fails
        try:
            sb = get_client()
            return sb.storage.from_(bucket).get_public_url(path)
        except Exception as e2:
            # If both fail, return a placeholder URL
            print(f"⚠️ Warning: Could not generate public URL for {bucket}/{path}: {e2}")
            return f"https://storage.supabase.co/{bucket}/{path}"