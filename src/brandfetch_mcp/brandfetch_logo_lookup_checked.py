"""
brandfetch_logo_lookup_checked.py

Robust, concurrency-safe implementation to:
- Try Brandfetch "logo by domain" endpoint first (high quota).
- Fall back to Brand API search (limited to BRAND_API_MONTH_LIMIT).
- Persist monthly Brand API usage counter in SQLite (safe across processes).
- Provide clear structured return values and warnings.

Configuration (env vars):
- BRANDFETCH_LOGO_API_URL: e.g. "https://api.brandfetch.io/logo?domain={domain}"
- BRANDFETCH_BRAND_API_URL: e.g. "https://api.brandfetch.io/brand/search?q={q}"
- BRANDFETCH_CLIENT_ID: Bearer token for logo-by-domain (high quota)
- BRANDFETCH_API_KEY: Bearer token for Brand API (limited)
- BRANDFETCH_DB_PATH: path to sqlite DB file (default: brand_api_usage.db)
- BRAND_API_MONTH_LIMIT: integer (default 100)
- BRAND_API_WARN_THRESHOLD: integer (default 90)
- BRANDFETCH_REQUEST_TIMEOUT_SEC: integer seconds for HTTP requests (default 8)
"""
import os
import re
import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import logging

# Use httpx instead of requests for async compatibility
import httpx

# Configure logging
logger = logging.getLogger("brandfetch-logo-lookup")

# Config with sensible defaults
LOGO_API_URL = os.getenv("BRANDFETCH_LOGO_API_URL", "https://api.brandfetch.io/v2/logo/{domain}")
BRAND_API_URL = os.getenv("BRANDFETCH_BRAND_API_URL", "https://api.brandfetch.io/v2/search/{q}")
LOGO_API_KEY = os.getenv("BRANDFETCH_CLIENT_ID")
BRAND_API_KEY = os.getenv("BRANDFETCH_API_KEY")
CLIENT_ID = os.getenv("BRANDFETCH_CLIENT_ID")
DB_PATH = os.getenv("BRANDFETCH_DB_PATH", "brand_api_usage.db")
BRAND_API_MONTH_LIMIT = int(os.getenv("BRAND_API_MONTH_LIMIT", "100"))
BRAND_API_WARN_THRESHOLD = int(os.getenv("BRAND_API_WARN_THRESHOLD", "90"))
REQUEST_TIMEOUT = int(os.getenv("BRANDFETCH_REQUEST_TIMEOUT_SEC", "8"))

IMAGE_EXTENSIONS = (".png", ".svg", ".jpg", ".jpeg", ".webp", ".gif", ".ico")


# ----------------------
# Client ID helper for hotlinking compliance
# ----------------------
def _append_client_id(url: str) -> str:
    """
    Append client ID to CDN URLs for Brandfetch hotlinking compliance.
    Only applies to cdn.brandfetch.io URLs.
    """
    if not CLIENT_ID:
        if "cdn.brandfetch.io" in url:
            logger.warning("Logo URL returned without client ID - may violate Brandfetch ToS. Set BRANDFETCH_CLIENT_ID for compliance")
        return url
    
    parsed = urlparse(url)
    if "cdn.brandfetch.io" not in parsed.netloc:
        return url
    
    # Parse existing query parameters
    query_params = parse_qs(parsed.query)
    query_params['c'] = [CLIENT_ID]
    
    # Rebuild URL with client ID
    new_parsed = parsed._replace(query=urlencode(query_params, doseq=True))
    return urlunparse(new_parsed)


# ----------------------
# Database (SQLite) for usage counting
# ----------------------
def _init_db(conn: sqlite3.Connection) -> None:
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS brand_api_usage (
                month TEXT PRIMARY KEY,
                count INTEGER NOT NULL
            )
            """
        )


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=5, check_same_thread=False)
    _init_db(conn)
    return conn


def get_brand_count() -> int:
    """Get current month's Brand API usage count."""
    month = datetime.utcnow().strftime("%Y-%m")
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT count FROM brand_api_usage WHERE month = ?", (month,))
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0


def increment_brand_counter(delta: int = 1) -> int:
    """Increment Brand API usage counter and return new count."""
    month = datetime.utcnow().strftime("%Y-%m")
    conn = _get_conn()
    with conn:
        cur = conn.execute("SELECT count FROM brand_api_usage WHERE month = ?", (month,))
        row = cur.fetchone()
        if row:
            new_count = int(row[0]) + delta
            conn.execute("UPDATE brand_api_usage SET count = ? WHERE month = ?", (new_count, month))
        else:
            new_count = delta
            conn.execute("INSERT INTO brand_api_usage (month, count) VALUES (?, ?)", (month, new_count))
    conn.close()
    return new_count


# ----------------------
# Helpers for parsing and extracting image URLs from API responses
# ----------------------
URL_RE = re.compile(r"https?://[^\s'\"<>]+", flags=re.IGNORECASE)


def _find_image_urls_in_obj(obj: Any) -> List[str]:
    """
    Recursively search a JSON-like object for strings that look like image URLs.
    Returns a list of candidate URLs (may contain duplicates).
    """
    found = []

    if isinstance(obj, str):
        # quick check for direct URL and image extension
        if obj.startswith("http://") or obj.startswith("https://"):
            if obj.lower().endswith(IMAGE_EXTENSIONS) or any(ext in obj.lower() for ext in IMAGE_EXTENSIONS):
                found.append(obj)
            else:
                # also allow image URLs without extension (e.g., endpoints that deliver images)
                found.append(obj)
        else:
            # extract embedded URLs from strings
            for m in URL_RE.findall(obj):
                if m.lower().endswith(IMAGE_EXTENSIONS) or any(ext in m.lower() for ext in IMAGE_EXTENSIONS):
                    found.append(m)
                else:
                    found.append(m)
    elif isinstance(obj, dict):
        for v in obj.values():
            found.extend(_find_image_urls_in_obj(v))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_find_image_urls_in_obj(item))

    # Deduplicate while preserving order
    seen = set()
    out = []
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def _extract_best_logo_from_response(resp_json: Any) -> Optional[str]:
    """
    Heuristic: look for common fields and image URLs in the JSON response.
    Return the first candidate image URL or None.
    """
    if resp_json is None:
        return None

    # common top-level keys to check first
    for key in ("logo", "logos", "image", "images", "icon", "icons", "data", "brand"):
        if isinstance(resp_json, dict) and key in resp_json:
            candidates = _find_image_urls_in_obj(resp_json[key])
            if candidates:
                return candidates[0]

    # fallback: search entire object
    candidates = _find_image_urls_in_obj(resp_json)
    return candidates[0] if candidates else None


# ----------------------
# API callers (async)
# ----------------------
async def call_logo_api(domain: str) -> Dict[str, Any]:
    """
    Call the logo-by-domain endpoint. Returns dict with keys:
    - status_code
    - json (if parseable) or None
    - text (raw text) if available
    - candidates (list of image URLs found)
    """
    if not LOGO_API_KEY:
        raise RuntimeError("Missing BRANDFETCH_LOGO_KEY environment variable")

    url = LOGO_API_URL.format(domain=domain)
    headers = {"Authorization": f"Bearer {LOGO_API_KEY}"}
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
    except Exception as ex:
        logger.warning(f"Logo API network error for {domain}: {ex}")
        return {"status_code": None, "error": str(ex), "json": None, "candidates": []}

    content_type = resp.headers.get("content-type", "")
    parsed = None
    if "application/json" in content_type:
        try:
            parsed = resp.json()
        except Exception:
            parsed = None
    else:
        # try to parse JSON even if content-type is missing/mis-set
        try:
            parsed = resp.json()
        except Exception:
            parsed = None

    parsed_candidates = _find_image_urls_in_obj(parsed) if parsed else []
    text_candidates = _find_image_urls_in_obj(resp.text if resp.text else "")

    all_candidates = []
    for c in parsed_candidates + text_candidates:
        if c not in all_candidates:
            # Apply client ID for hotlinking compliance
            all_candidates.append(_append_client_id(c))

    return {
        "status_code": resp.status_code,
        "json": parsed,
        "text": resp.text,
        "candidates": all_candidates,
    }


async def call_brand_api_search(query: str) -> Dict[str, Any]:
    """
    Call the Brand API search endpoint. Returns a dict similar to call_logo_api.
    """
    if not BRAND_API_KEY:
        raise RuntimeError("Missing BRANDFETCH_BRAND_KEY environment variable")

    url = BRAND_API_URL.format(q=query)
    headers = {"Authorization": f"Bearer {BRAND_API_KEY}"}
    
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.get(url, headers=headers)
    except Exception as ex:
        logger.warning(f"Brand API network error for query '{query}': {ex}")
        return {"status_code": None, "error": str(ex), "json": None, "candidates": []}

    parsed = None
    content_type = resp.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            parsed = resp.json()
        except Exception:
            parsed = None
    else:
        try:
            parsed = resp.json()
        except Exception:
            parsed = None

    parsed_candidates = _find_image_urls_in_obj(parsed) if parsed else []
    text_candidates = _find_image_urls_in_obj(resp.text if resp.text else "")

    all_candidates = []
    for c in parsed_candidates + text_candidates:
        if c not in all_candidates:
            # Apply client ID for hotlinking compliance
            all_candidates.append(_append_client_id(c))

    return {
        "status_code": resp.status_code,
        "json": parsed,
        "text": resp.text,
        "candidates": all_candidates,
    }


# ----------------------
# Matching logic
# ----------------------
def _domain_matches_logo_candidates(domain: str, candidates: List[str], resp_json: Optional[Any] = None) -> bool:
    """
    Heuristic match:
    - Any candidate URL contains the domain string, OR
    - resp_json contains a 'domain'/'host' field matching the domain.
    """
    domain = domain.lower()
    for c in candidates:
        if not c:
            continue
        if domain in c.lower():
            return True

    # check parsed json for obvious host/domain fields
    if isinstance(resp_json, dict):
        for k in ("host", "domain", "website", "url"):
            v = resp_json.get(k)
            if isinstance(v, str) and domain in v.lower():
                return True
        data = resp_json.get("data") or resp_json.get("brand") or {}
        if isinstance(data, dict):
            for k in ("host", "domain", "website", "url"):
                v = data.get(k)
                if isinstance(v, str) and domain in v.lower():
                    return True

    return False


# ----------------------
# Public wrapper
# ----------------------
async def get_logo_for_domain(domain: str, company_hint: Optional[str] = None) -> Dict[str, Any]:
    """
    Orchestrator:
    1) Try logo-by-domain.
    2) If found and matches, return it with source 'domain-logo'.
    3) Otherwise, check Brand API usage and optionally call Brand API search.
    """
    domain = domain.strip().lower()
    if not domain:
        return {"error": "invalid_domain", "message": "Empty domain provided"}

    logger.info(f"Starting logo lookup for domain: {domain}")

    # 1) domain logo lookup
    domain_resp = await call_logo_api(domain)
    domain_candidates = domain_resp.get("candidates", []) or []
    
    if domain_resp.get("status_code") == 200 and domain_candidates:
        if _domain_matches_logo_candidates(domain, domain_candidates, domain_resp.get("json")):
            logger.info(f"Found matching logo via domain lookup for {domain}")
            return {
                "logo_url": domain_candidates[0],
                "source": "domain-logo",
                "reason": "domain lookup returned matching candidate",
                "domain_resp": {"status_code": domain_resp.get("status_code")},
                "brand_api_calls_this_month": get_brand_count(),
            }

    # 2) Brand API fallback
    current_count = get_brand_count()
    if current_count >= BRAND_API_MONTH_LIMIT:
        logger.warning(f"Brand API limit reached ({BRAND_API_MONTH_LIMIT}) for {domain}")
        return {
            "error": "brand_api_limit_reached",
            "message": f"Brand API monthly limit reached ({BRAND_API_MONTH_LIMIT}).",
            "brand_api_calls_this_month": current_count,
        }

    warning = None
    if current_count >= BRAND_API_WARN_THRESHOLD:
        warning = "warning: approaching Brand API monthly limit"
        logger.warning(f"Approaching Brand API limit: {current_count}/{BRAND_API_MONTH_LIMIT}")

    query = company_hint or domain
    logger.info(f"Falling back to Brand API search for query: {query}")
    brand_resp = await call_brand_api_search(query)

    # If brand_resp had no status_code (e.g., network error), return that error without incrementing.
    if brand_resp.get("status_code") is None:
        logger.error(f"Brand API network error for {domain}: {brand_resp.get('error')}")
        return {
            "error": "brand_api_network_error",
            "message": brand_resp.get("error", "network error while calling Brand API"),
            "brand_api_calls_this_month": current_count,
        }

    # increment usage because we performed a Brand API call that returned a response
    new_count = increment_brand_counter(1)
    logger.info(f"Incremented Brand API count to {new_count}")

    # pick best candidate
    brand_candidates = brand_resp.get("candidates", []) or []
    best = brand_candidates[0] if brand_candidates else None
    
    if best:
        logger.info(f"Found logo via Brand API fallback for {domain}: {best}")
        return {
            "logo_url": best,
            "source": "brand-search",
            "reason": "domain lookup failed or mismatch; used Brand API fallback",
            "brand_api_calls_this_month": new_count,
            "warning": warning,
            "brand_resp_status": brand_resp.get("status_code"),
        }

    # no logo found in Brand API response
    logger.warning(f"No logo found for {domain} in domain or Brand API search")
    return {
        "error": "no_logo_found",
        "message": "No logo candidate was found from domain lookup or Brand API search",
        "brand_api_calls_this_month": new_count,
        "warning": warning,
    }


def get_status() -> Dict[str, Any]:
    """Get current usage status."""
    current_count = get_brand_count()
    month = datetime.utcnow().strftime("%Y-%m")
    
    return {
        "brand_api_calls_this_month": current_count,
        "month": month,
        "limit": BRAND_API_MONTH_LIMIT,
        "remaining": max(0, BRAND_API_MONTH_LIMIT - current_count),
        "warning_threshold": BRAND_API_WARN_THRESHOLD,
        "approaching_limit": current_count >= BRAND_API_WARN_THRESHOLD,
    }
