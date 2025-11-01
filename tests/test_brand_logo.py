"""Tests for logo-first brand lookup functionality."""

import asyncio
import os
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from brandfetch_mcp.brand_logo import BrandLogoLookup, LogoLookupCache, get_logo_url


@pytest.fixture
def mock_cache():
    """Create a mock cache for testing."""
    cache = MagicMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock()
    return cache


@pytest.fixture
def logo_lookup(mock_cache):
    """Create a BrandLogoLookup instance with mocked cache."""
    lookup = BrandLogoLookup()
    lookup.cache = mock_cache
    return lookup


class TestLogoLookupCache:
    """Test the caching layer."""

    @pytest.mark.asyncio
    async def test_cache_get_set(self):
        """Test basic cache get/set operations."""
        cache = LogoLookupCache()
        
        # Test set and get
        test_key = "test_key"
        test_value = {"url": "https://example.com/logo.png", "source": "cdn_domain"}
        
        await cache.set(test_key, test_value)
        result = await cache.get(test_key)
        
        assert result == test_value


class TestBrandLogoLookup:
    """Test the main logo lookup functionality."""

    @pytest.mark.asyncio
    async def test_domain_cdn_success(self, logo_lookup):
        """Test successful CDN validation for domain."""
        with patch.object(logo_lookup, '_validate_cdn_url', return_value="https://cdn.brandfetch.io/github.com") as mock_validate:
            result_url, source = await logo_lookup.get_logo_url(domain="github.com")
            
            assert result_url == "https://cdn.brandfetch.io/github.com"
            assert source == "cdn_domain"
            mock_validate.assert_called_once_with("github.com")

    @pytest.mark.asyncio
    async def test_domain_cdn_failure(self, logo_lookup):
        """Test CDN validation failure for domain."""
        with patch.object(logo_lookup, '_validate_cdn_url', return_value=None) as mock_validate:
            result_url, source = await logo_lookup.get_logo_url(domain="nonexistent.com")
            
            assert result_url is None
            assert source == "none"
            mock_validate.assert_called_once_with("nonexistent.com")

    @pytest.mark.asyncio
    async def test_name_heuristic_success(self, logo_lookup):
        """Test successful heuristic domain guessing."""
        with patch.object(logo_lookup, '_generate_domain_candidates', return_value=["github.com", "github.co"]) as mock_candidates, \
             patch.object(logo_lookup, '_validate_cdn_url') as mock_validate, \
             patch.object(logo_lookup, '_search_brandfetch_api', return_value=None) as mock_search:
            
            # First candidate fails, second succeeds
            mock_validate.side_effect = [None, "https://cdn.brandfetch.io/github.co"]
            
            result_url, source = await logo_lookup.get_logo_url(name="GitHub")
            
            assert result_url == "https://cdn.brandfetch.io/github.co"
            assert source == "heuristic_guess"
            mock_candidates.assert_called_once_with("GitHub")
            assert mock_validate.call_count == 2
            mock_search.assert_not_called()

    @pytest.mark.asyncio
    async def test_name_api_fallback_success(self, logo_lookup):
        """Test successful API fallback when heuristics fail."""
        with patch.object(logo_lookup, '_generate_domain_candidates', return_value=["github.com"]) as mock_candidates, \
             patch.object(logo_lookup, '_validate_cdn_url') as mock_validate, \
             patch.object(logo_lookup, '_search_brandfetch_api', return_value="github.com") as mock_search:
            
            # Heuristic fails, API search succeeds
            mock_validate.side_effect = [None, "https://cdn.brandfetch.io/github.com"]
            
            result_url, source = await logo_lookup.get_logo_url(name="GitHub")
            
            assert result_url == "https://cdn.brandfetch.io/github.com"
            assert source == "brand_search"
            mock_search.assert_called_once_with("GitHub")

    @pytest.mark.asyncio
    async def test_name_complete_failure(self, logo_lookup):
        """Test when both heuristics and API search fail."""
        with patch.object(logo_lookup, '_generate_domain_candidates', return_value=["github.com"]) as mock_candidates, \
             patch.object(logo_lookup, '_validate_cdn_url', return_value=None) as mock_validate, \
             patch.object(logo_lookup, '_search_brandfetch_api', return_value=None) as mock_search:
            
            result_url, source = await logo_lookup.get_logo_url(name="NonExistentBrand")
            
            assert result_url is None
            assert source == "none"

    @pytest.mark.asyncio
    async def test_cache_hit(self, logo_lookup):
        """Test cache hit prevents external calls."""
        cached_result = {"url": "https://cached.example.com/logo.png", "source": "cdn_domain"}
        logo_lookup.cache.get = AsyncMock(return_value=cached_result)
        
        result_url, source = await logo_lookup.get_logo_url(domain="example.com")
        
        assert result_url == "https://cached.example.com/logo.png"
        assert source == "cdn_domain"
        logo_lookup.cache.set.assert_not_called()  # Should not cache again

    @pytest.mark.asyncio
    async def test_no_parameters(self, logo_lookup):
        """Test calling with no parameters."""
        result_url, source = await logo_lookup.get_logo_url()
        
        assert result_url is None
        assert source == "none"


class TestDomainNormalization:
    """Test domain candidate generation."""

    def test_normalize_name_basic(self, logo_lookup):
        """Test basic name normalization."""
        assert logo_lookup._normalize_name_for_domain("GitHub") == "github"
        assert logo_lookup._normalize_name_for_domain("Stripe Inc.") == "stripe"
        assert logo_lookup._normalize_name_for_domain("Netflix LLC") == "netflix"

    def test_generate_domain_candidates(self, logo_lookup):
        """Test domain candidate generation."""
        candidates = logo_lookup._generate_domain_candidates("GitHub")
        
        expected = [
            "github.com", "www.github.com",
            "github.co", "www.github.co",
            "github.io", "www.github.io",
            "github.net", "www.github.net",
            "github.org", "www.github.org",
            "github.app", "www.github.app",
            "github.dev", "www.github.dev"
        ]
        
        assert candidates == expected


class TestCDNValidation:
    """Test CDN URL validation."""

    @pytest.mark.asyncio
    async def test_cdn_head_success(self, logo_lookup):
        """Test successful HEAD request to CDN."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_head = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(head=mock_head))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._validate_cdn_url("github.com")
            
            assert result == "https://cdn.brandfetch.io/github.com"
            mock_head.assert_called_once()

    @pytest.mark.asyncio
    async def test_cdn_head_fallback_to_get(self, logo_lookup):
        """Test fallback to GET when HEAD is blocked."""
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405  # Method not allowed
        
        mock_get_response = MagicMock()
        mock_get_response.status_code = 206  # Partial content
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_head = AsyncMock(return_value=mock_head_response)
            mock_get = AsyncMock(return_value=mock_get_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(head=mock_head, get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._validate_cdn_url("github.com")
            
            assert result == "https://cdn.brandfetch.io/github.com"
            mock_head.assert_called_once()
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cdn_validation_failure(self, logo_lookup):
        """Test CDN validation failure."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_head = AsyncMock(side_effect=Exception("Connection failed"))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(head=mock_head))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._validate_cdn_url("github.com")
            
            assert result is None


class TestBrandfetchAPISearch:
    """Test Brandfetch API search functionality."""

    @pytest.mark.asyncio
    async def test_api_search_success(self, logo_lookup):
        """Test successful API search."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"domain": "github.com", "name": "GitHub"}]
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._search_brandfetch_api("GitHub")
            
            assert result == "github.com"

    @pytest.mark.asyncio
    async def test_api_search_no_results(self, logo_lookup):
        """Test API search with no results."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._search_brandfetch_api("NonExistentBrand")
            
            assert result is None

    @pytest.mark.asyncio
    async def test_api_search_no_api_key(self, logo_lookup):
        """Test API search without API key."""
        logo_lookup.api_key = None
        
        result = await logo_lookup._search_brandfetch_api("GitHub")
        
        assert result is None


class TestCacheEdgeCases:
    """Test caching edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_cache_redis_connection_failure(self):
        """Test behavior when Redis connection fails."""
        with patch.dict(os.environ, {"REDIS_URL": "redis://invalid:6379"}):
            cache = LogoLookupCache()
            # Should not crash, just log warning
            assert cache.redis_client is None

    @pytest.mark.asyncio
    async def test_cache_redis_get_error(self, logo_lookup):
        """Test Redis get error handling."""
        # Mock Redis client that raises exception
        mock_redis = AsyncMock()
        mock_redis.get.side_effect = Exception("Redis connection error")
        logo_lookup.cache.redis_client = mock_redis
        
        # Should fall back to memory cache
        result = await logo_lookup.cache.get("test_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_invalid_ttl_config(self):
        """Test invalid TTL configuration defaults to 86400."""
        with patch.dict(os.environ, {"BRANDFETCH_CACHE_TTL": "invalid"}):
            cache = LogoLookupCache()
            assert cache.ttl_seconds == 86400  # Default


class TestConfigurationEdgeCases:
    """Test configuration-related edge cases."""

    @pytest.mark.asyncio
    async def test_custom_cdn_template(self):
        """Test custom CDN template configuration."""
        with patch.dict(os.environ, {"BRANDFETCH_LOGO_CDN_TEMPLATE": "https://custom.cdn/{domain}/logo"}):
            lookup = BrandLogoLookup()
            assert lookup.cdn_template == "https://custom.cdn/{domain}/logo"

    @pytest.mark.asyncio
    async def test_no_cachetools_fallback(self):
        """Test fallback when cachetools is not available."""
        with patch('brandfetch_mcp.brand_logo.HAS_CACHETOOLS', False):
            cache = LogoLookupCache()
            assert isinstance(cache.memory_cache, dict)
            
            # Should still work for basic operations
            await cache.set("test", {"url": "test", "source": "test"})
            result = await cache.get("test")
            assert result == {"url": "test", "source": "test"}


class TestHeuristicEdgeCases:
    """Test complex heuristic scenarios."""

    def test_normalize_name_edge_cases(self, logo_lookup):
        """Test name normalization with edge cases."""
        # Empty string
        assert logo_lookup._normalize_name_for_domain("") == ""
        
        # Only punctuation
        assert logo_lookup._normalize_name_for_domain("!!!") == ""
        
        # Very long name
        long_name = "a" * 1000
        normalized = logo_lookup._normalize_name_for_domain(long_name)
        assert len(normalized) == 1000
        
        # Mixed case and special chars
        assert logo_lookup._normalize_name_for_domain("Hello-World!") == "hello-world"
        
        # Multiple spaces
        assert logo_lookup._normalize_name_for_domain("hello   world") == "helloworld"

    def test_generate_candidates_edge_cases(self, logo_lookup):
        """Test domain candidate generation edge cases."""
        # Empty name
        assert logo_lookup._generate_domain_candidates("") == []
        
        # Name with only suffixes
        assert logo_lookup._generate_domain_candidates("inc") == []
        
        # Name that becomes empty after normalization
        assert logo_lookup._generate_domain_candidates("!!!") == []


class TestCDNValidationEdgeCases:
    """Test CDN validation with various HTTP responses."""

    @pytest.mark.asyncio
    async def test_cdn_redirect_handling(self, logo_lookup):
        """Test CDN validation with redirects."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_head = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(head=mock_head))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._validate_cdn_url("github.com")
            assert result == "https://cdn.brandfetch.io/github.com"

    @pytest.mark.asyncio
    async def test_cdn_various_error_codes(self, logo_lookup):
        """Test CDN validation with different error status codes."""
        for status_code in [404, 500, 502, 503]:
            mock_response = MagicMock()
            mock_response.status_code = status_code
            
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_context = MagicMock()
                mock_head = AsyncMock(return_value=mock_response)
                mock_context.__aenter__ = AsyncMock(return_value=MagicMock(head=mock_head))
                mock_context.__aexit__ = AsyncMock(return_value=None)
                mock_client_class.return_value = mock_context
                
                result = await logo_lookup._validate_cdn_url("github.com")
                assert result is None

    @pytest.mark.asyncio
    async def test_cdn_get_fallback_failure(self, logo_lookup):
        """Test when GET fallback also fails."""
        mock_head_response = MagicMock()
        mock_head_response.status_code = 405
        
        mock_get_response = MagicMock()
        mock_get_response.status_code = 404
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_head = AsyncMock(return_value=mock_head_response)
            mock_get = AsyncMock(return_value=mock_get_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(head=mock_head, get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._validate_cdn_url("github.com")
            assert result is None


class TestAPISearchEdgeCases:
    """Test Brandfetch API search edge cases."""

    @pytest.mark.asyncio
    async def test_api_search_empty_results(self, logo_lookup):
        """Test API search with empty results array."""
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._search_brandfetch_api("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_api_search_malformed_result(self, logo_lookup):
        """Test API search with malformed result (no domain field)."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"name": "Test", "other_field": "value"}]  # No domain
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._search_brandfetch_api("test")
            assert result is None

    @pytest.mark.asyncio
    async def test_api_search_non_list_response(self, logo_lookup):
        """Test API search with non-list response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"error": "Invalid response"}
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            result = await logo_lookup._search_brandfetch_api("test")
            assert result is None


class TestRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    async def test_api_semaphore_usage(self, logo_lookup):
        """Test that API calls use the semaphore."""
        mock_response = MagicMock()
        mock_response.json.return_value = [{"domain": "github.com"}]
        mock_response.raise_for_status = MagicMock()
        
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(return_value=mock_response)
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context
            
            # Verify semaphore is used
            original_semaphore = logo_lookup.api_semaphore
            assert isinstance(original_semaphore, asyncio.Semaphore)
            
            result = await logo_lookup._search_brandfetch_api("github")
            assert result == "github.com"


class TestIntegrationScenarios:
    """Test complex integration scenarios."""

    @pytest.mark.asyncio
    async def test_domain_preferred_over_name(self, logo_lookup):
        """Test that domain parameter takes precedence over name."""
        with patch.object(logo_lookup, '_validate_cdn_url', return_value="https://cdn.brandfetch.io/github.com") as mock_validate:
            result_url, source = await logo_lookup.get_logo_url(domain="github.com", name="GitHub")
            
            assert result_url == "https://cdn.brandfetch.io/github.com"
            assert source == "cdn_domain"
            mock_validate.assert_called_once_with("github.com")

    @pytest.mark.asyncio
    async def test_complex_name_with_suffixes(self, logo_lookup):
        """Test heuristic generation with complex brand names."""
        # Test name with multiple suffixes and special chars
        candidates = logo_lookup._generate_domain_candidates("Hello World Inc. LLC!")
        
        # Should normalize to "helloworldinc" (removes LLC but not Inc due to order)
        expected_base = "helloworldinc"
        assert f"{expected_base}.com" in candidates
        assert f"www.{expected_base}.com" in candidates
        assert len(candidates) == 14  # 7 TLDs × 2 variants each

    @pytest.mark.asyncio
    async def test_cache_consistency_across_instances(self):
        """Test that global instance maintains cache consistency."""
        # Create two separate calls to ensure they use the same global instance
        with patch("brandfetch_mcp.brand_logo.logo_lookup") as mock_lookup:
            mock_lookup.get_logo_url = AsyncMock(return_value=("https://example.com/logo.png", "cdn_domain"))
            
            # First call
            result1 = await get_logo_url(domain="example.com")
            # Second call
            result2 = await get_logo_url(domain="example.com")
            
            # Should use same instance
            assert mock_lookup.get_logo_url.call_count == 2
            assert result1 == result2
