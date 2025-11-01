"""Logo-first brand lookup with caching and heuristics."""

import asyncio
import logging
import os
import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import httpx
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger("brandfetch-mcp")

# Try to import caching libraries
try:
    from cachetools import TTLCache
    HAS_CACHETOOLS = True
except ImportError:
    HAS_CACHETOOLS = False
    logger.warning("cachetools not installed, caching disabled")

try:
    import redis.asyncio as redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class LogoLookupCache:
    """Caching layer for logo URL lookups."""

    def __init__(self):
        # Parse TTL with error handling
        try:
            self.ttl_seconds = int(os.getenv("BRANDFETCH_CACHE_TTL", "86400"))  # 24 hours default
        except (ValueError, TypeError):
            logger.warning("Invalid BRANDFETCH_CACHE_TTL value, using default of 86400 seconds")
            self.ttl_seconds = 86400

        # In-memory cache
        if HAS_CACHETOOLS:
            self.memory_cache = TTLCache(maxsize=1000, ttl=self.ttl_seconds)
        else:
            self.memory_cache = {}

        # Redis cache (optional)
        self.redis_client = None
        redis_url = os.getenv("REDIS_URL")
        if redis_url and HAS_REDIS:
            try:
                self.redis_client = redis.from_url(redis_url)
                logger.info("Redis cache enabled")
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
        elif redis_url and not HAS_REDIS:
            logger.warning("REDIS_URL set but redis library not available")

    async def get(self, key: str) -> Optional[Dict]:
        """Get cached result."""
        # Try Redis first
        if self.redis_client:
            try:
                cached = await self.redis_client.get(f"brandfetch:logo:{key}")
                if cached:
                    logger.debug(f"Redis cache hit for {key}")
                    return eval(cached)  # Safe since we control the data
            except Exception as e:
                logger.warning(f"Redis get error: {e}")

        # Try memory cache
        if HAS_CACHETOOLS and key in self.memory_cache:
            logger.debug(f"Memory cache hit for {key}")
            return self.memory_cache[key]
        elif not HAS_CACHETOOLS and key in self.memory_cache:
            logger.debug(f"Memory cache hit for {key}")
            return self.memory_cache[key]

        return None

    async def set(self, key: str, value: Dict):
        """Set cached result."""
        # Store in Redis
        if self.redis_client:
            try:
                await self.redis_client.setex(
                    f"brandfetch:logo:{key}",
                    self.ttl_seconds,
                    repr(value)
                )
            except Exception as e:
                logger.warning(f"Redis set error: {e}")

        # Store in memory
        if HAS_CACHETOOLS:
            self.memory_cache[key] = value
        else:
            self.memory_cache[key] = value


class BrandLogoLookup:
    """Fast logo URL lookup with domain heuristics and API fallback."""

    def __init__(self):
        self.cache = LogoLookupCache()
        # Backward compatibility: try new keys first, fall back to old key
        self.api_key = os.getenv("BRANDFETCH_LOGO_KEY") or os.getenv("BRANDFETCH_API_KEY")
        
        # Add deprecation warning if using old key pattern
        if os.getenv("BRANDFETCH_API_KEY") and not os.getenv("BRANDFETCH_LOGO_KEY"):
            logger.warning(
                "BRANDFETCH_API_KEY is deprecated. Use BRANDFETCH_LOGO_KEY for logo operations. "
                "Falling back to BRANDFETCH_API_KEY for backward compatibility."
            )
            
        self.cdn_template = os.getenv("BRANDFETCH_LOGO_CDN_TEMPLATE", "https://cdn.brandfetch.io/{domain}")

        # Rate limiting semaphore for API calls
        self.api_semaphore = asyncio.Semaphore(5)  # Max 5 concurrent API calls

        # HTTP client timeout
        self.timeout = httpx.Timeout(3.0, connect=2.0)

        # Domain heuristics: common TLDs to try
        self.common_tlds = [".com", ".co", ".io", ".net", ".org", ".app", ".dev"]

    def _normalize_name_for_domain(self, name: str) -> str:
        """Normalize brand name for domain guessing."""
        if not name:
            return ""

        # Convert to lowercase
        normalized = name.lower()

        # Remove punctuation and extra spaces
        normalized = re.sub(r'[^\w\s-]', '', normalized)
        normalized = re.sub(r'\s+', '', normalized)

        # Remove common suffixes
        suffixes = ['inc', 'llc', 'corp', 'corporation', 'company', 'co', 'ltd', 'limited', 'group', 'labs', 'studio']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)].rstrip('-')

        return normalized

    def _generate_domain_candidates(self, name: str) -> List[str]:
        """Generate potential domain names from brand name."""
        candidates = []
        normalized = self._normalize_name_for_domain(name)

        if not normalized:
            return candidates

        # Try different combinations
        for tld in self.common_tlds:
            candidates.append(f"{normalized}{tld}")
            candidates.append(f"www.{normalized}{tld}")

        return candidates

    async def _validate_cdn_url(self, domain: str) -> Optional[str]:
        """Validate if logo exists at CDN URL."""
        cdn_url = self.cdn_template.format(domain=domain)

        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                # Try HEAD request first (cheaper)
                response = await client.head(cdn_url)
                if response.status_code == 200:
                    logger.debug(f"CDN HEAD success for {domain}: {cdn_url}")
                    return cdn_url

                # If HEAD fails but not definitively blocked, try small GET
                if response.status_code in (405, 403):  # Method not allowed or forbidden
                    logger.debug(f"CDN HEAD blocked for {domain}, trying GET")
                    response = await client.get(cdn_url, headers={"Range": "bytes=0-1023"})  # First 1KB
                    if response.status_code == 206:  # Partial content
                        logger.debug(f"CDN GET success for {domain}: {cdn_url}")
                        return cdn_url

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.debug(f"CDN validation failed for {domain}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error validating CDN for {domain}: {e}")

        return None

    async def _search_brandfetch_api(self, name: str) -> Optional[str]:
        """Search Brandfetch API for brand and return domain."""
        if not self.api_key:
            logger.warning("No API key available. Set BRANDFETCH_LOGO_KEY or BRANDFETCH_API_KEY to search API")
            return None

        async with self.api_semaphore:  # Rate limit API calls
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                search_url = f"https://api.brandfetch.io/v2/search/{name}"

                async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                    response = await client.get(search_url, headers=headers)
                    response.raise_for_status()

                    results = response.json()
                    if isinstance(results, list) and results:
                        # Return first result's domain
                        domain = results[0].get("domain")
                        if domain:
                            logger.info(f"Brandfetch search found domain {domain} for name '{name}'")
                            return domain

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    logger.error("Invalid Brandfetch API key")
                else:
                    logger.warning(f"Brandfetch API error: {e.response.status_code}")
            except Exception as e:
                logger.warning(f"Brandfetch search failed for '{name}': {e}")

        return None

    async def get_logo_url(
        self,
        domain: Optional[str] = None,
        name: Optional[str] = None
    ) -> Tuple[Optional[str], str]:
        """
        Get logo URL for a brand.

        Args:
            domain: Known domain (preferred, fastest path)
            name: Brand name to search (fallback with heuristics)

        Returns:
            Tuple of (logo_url_or_None, source)
            source is one of: 'cdn_domain', 'heuristic_guess', 'brand_search', 'none'
        """
        if not domain and not name:
            return None, "none"

        # Create cache key
        cache_key = f"domain:{domain}" if domain else f"name:{name}"

        # Check cache first
        cached_result = await self.cache.get(cache_key)
        if cached_result:
            logger.debug(f"Cache hit for {cache_key}")
            return cached_result["url"], cached_result["source"]

        result_url = None
        source = "none"

        # Domain path (fastest)
        if domain:
            logger.info(f"Trying CDN validation for domain: {domain}")
            result_url = await self._validate_cdn_url(domain)
            if result_url:
                source = "cdn_domain"
            else:
                logger.debug(f"CDN validation failed for domain: {domain}")

        # Name path with heuristics
        elif name:
            logger.info(f"Trying heuristics for name: {name}")
            candidates = self._generate_domain_candidates(name)

            for candidate in candidates[:5]:  # Limit to first 5 candidates
                logger.debug(f"Trying candidate domain: {candidate}")
                result_url = await self._validate_cdn_url(candidate)
                if result_url:
                    source = "heuristic_guess"
                    break

            # If heuristics fail, try Brandfetch API search
            if not result_url:
                logger.info(f"Heuristics failed for '{name}', trying Brandfetch search")
                found_domain = await self._search_brandfetch_api(name)
                if found_domain:
                    result_url = await self._validate_cdn_url(found_domain)
                    if result_url:
                        source = "brand_search"

        # Cache the result
        if result_url or source == "none":
            await self.cache.set(cache_key, {"url": result_url, "source": source})

        logger.info(f"Logo lookup result: url={result_url}, source={source}")
        return result_url, source


# Global instance
logo_lookup = BrandLogoLookup()


async def get_logo_url(
    domain: Optional[str] = None,
    name: Optional[str] = None
) -> Tuple[Optional[str], str]:
    """
    Get logo URL for a brand.

    This is the main entry point for logo lookups. It tries multiple strategies
    in order of speed and reliability:
    1. Direct CDN validation for known domains
    2. Heuristic domain guessing for brand names
    3. Brandfetch API search as final fallback

    Args:
        domain: Known domain (e.g., 'github.com')
        name: Brand name (e.g., 'GitHub')

    Returns:
        Tuple of (logo_url, source) where source indicates how the URL was found:
        - 'cdn_domain': Direct CDN validation succeeded
        - 'heuristic_guess': Domain guessed from name and validated
        - 'brand_search': Found via Brandfetch API search
        - 'none': No logo URL found
    """
    return await logo_lookup.get_logo_url(domain=domain, name=name)
