"""Tests for the brandfetch_logo_lookup_checked module."""

import pytest
import tempfile
import os
from unittest.mock import patch, AsyncMock, MagicMock
import sqlite3

from brandfetch_mcp.brandfetch_logo_lookup_checked import (
    get_logo_for_domain,
    get_brand_count,
    increment_brand_counter,
    get_status,
    call_logo_api,
    call_brand_api_search,
    _domain_matches_logo_candidates,
    _find_image_urls_in_obj,
)


class TestDatabaseFunctions:
    """Test SQLite-based usage tracking."""

    def setup_method(self):
        """Set up a temporary database for each test."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Patch the DB_PATH to use our temp database
        self.db_patcher = patch('brandfetch_mcp.brandfetch_logo_lookup_checked.DB_PATH', self.temp_db.name)
        self.db_patcher.start()

    def teardown_method(self):
        """Clean up the temporary database."""
        self.db_patcher.stop()
        os.unlink(self.temp_db.name)

    def test_get_brand_count_empty(self):
        """Test getting count when no entries exist."""
        count = get_brand_count()
        assert count == 0

    def test_increment_brand_counter(self):
        """Test incrementing the counter."""
        # First increment
        count = increment_brand_counter(1)
        assert count == 1
        
        # Second increment
        count = increment_brand_counter(2)
        assert count == 3
        
        # Verify get_brand_count returns the same
        count = get_brand_count()
        assert count == 3

    def test_get_status(self):
        """Test getting status information."""
        increment_brand_counter(5)
        status = get_status()
        
        assert status["brand_api_calls_this_month"] == 5
        assert status["limit"] == 100  # default
        assert status["remaining"] == 95
        assert status["approaching_limit"] == False


class TestURLExtraction:
    """Test URL extraction and matching functions."""

    def test_find_image_urls_in_obj_string(self):
        """Test finding URLs in strings."""
        obj = "https://example.com/logo.svg"
        urls = _find_image_urls_in_obj(obj)
        assert "https://example.com/logo.svg" in urls

    def test_find_image_urls_in_obj_dict(self):
        """Test finding URLs in dictionaries."""
        obj = {"logo": "https://example.com/logo.png", "website": "https://example.com"}
        urls = _find_image_urls_in_obj(obj)
        assert "https://example.com/logo.png" in urls

    def test_find_image_urls_in_obj_list(self):
        """Test finding URLs in lists."""
        obj = ["https://example.com/logo.svg", "https://example.com/icon.png"]
        urls = _find_image_urls_in_obj(obj)
        assert len(urls) == 2
        assert "https://example.com/logo.svg" in urls
        assert "https://example.com/icon.png" in urls

    def test_find_image_urls_deduplication(self):
        """Test that duplicate URLs are removed."""
        obj = ["https://example.com/logo.svg", "https://example.com/logo.svg"]
        urls = _find_image_urls_in_obj(obj)
        assert len(urls) == 1
        assert urls[0] == "https://example.com/logo.svg"

    def test_domain_matches_logo_candidates(self):
        """Test domain matching logic."""
        domain = "apple.com"
        candidates = ["https://cdn.brandfetch.io/apple.com/logo.svg", "https://example.com/logo.png"]
        
        assert _domain_matches_logo_candidates(domain, candidates) == True

    def test_domain_matches_logo_candidates_no_match(self):
        """Test domain matching when no match exists."""
        domain = "apple.com"
        candidates = ["https://cdn.brandfetch.io/google.com/logo.svg", "https://example.com/logo.png"]
        
        assert _domain_matches_logo_candidates(domain, candidates) == False

    def test_domain_matches_logo_candidates_json_field(self):
        """Test domain matching via JSON field."""
        domain = "apple.com"
        candidates = ["https://example.com/logo.png"]
        resp_json = {"domain": "apple.com", "logo": "https://example.com/logo.png"}
        
        assert _domain_matches_logo_candidates(domain, candidates, resp_json) == True


class TestAPICallers:
    """Test API calling functions."""

    @pytest.mark.asyncio
    async def test_call_logo_api_success(self):
        """Test successful logo API call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"logo": "https://example.com/logo.svg"}
        mock_response.text = '{"logo": "https://example.com/logo.svg"}'

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.httpx.AsyncClient') as mock_client, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.LOGO_API_KEY', 'test_key'):
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await call_logo_api("apple.com")
            
            assert result["status_code"] == 200
            assert "https://example.com/logo.svg" in result["candidates"]
            assert len(result["candidates"]) > 0

    @pytest.mark.asyncio
    async def test_call_logo_api_missing_key(self):
        """Test logo API call with missing API key."""
        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.LOGO_API_KEY', None):
            with pytest.raises(RuntimeError, match="Missing BRANDFETCH_CLIENT_ID"):
                await call_logo_api("apple.com")

    @pytest.mark.asyncio
    async def test_call_brand_api_search_success(self):
        """Test successful brand API search call."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = [{"domain": "apple.com", "logo": "https://example.com/logo.svg"}]
        mock_response.text = '[{"domain": "apple.com", "logo": "https://example.com/logo.svg"}]'

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.httpx.AsyncClient') as mock_client, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.BRAND_API_KEY', 'test_key'):
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
            
            result = await call_brand_api_search("apple")
            
            assert result["status_code"] == 200
            assert len(result["candidates"]) > 0

    @pytest.mark.asyncio
    async def test_call_brand_api_search_missing_key(self):
        """Test brand API search call with missing API key."""
        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.BRAND_API_KEY', None):
            with pytest.raises(RuntimeError, match="Missing BRANDFETCH_API_KEY"):
                await call_brand_api_search("apple")


class TestGetLogoForDomain:
    """Test the main get_logo_for_domain function."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        
        # Patch the DB_PATH to use our temp database
        self.db_patcher = patch('brandfetch_mcp.brandfetch_logo_lookup_checked.DB_PATH', self.temp_db.name)
        self.db_patcher.start()

    def teardown_method(self):
        """Clean up test environment."""
        self.db_patcher.stop()
        os.unlink(self.temp_db.name)

    @pytest.mark.asyncio
    async def test_domain_lookup_success(self):
        """Test successful domain lookup."""
        mock_domain_resp = {
            "status_code": 200,
            "candidates": ["https://cdn.brandfetch.io/apple.com/logo.svg"],
            "json": {"domain": "apple.com"}
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_logo_api', new_callable=AsyncMock) as mock_logo_api:
            mock_logo_api.return_value = mock_domain_resp
            
            result = await get_logo_for_domain("apple.com")
            
            assert result["logo_url"] == "https://cdn.brandfetch.io/apple.com/logo.svg"
            assert result["source"] == "domain-logo"
            assert result["reason"] == "domain lookup returned matching candidate"
            assert result["brand_api_calls_this_month"] == 0
            mock_logo_api.assert_called_once_with("apple.com")

    @pytest.mark.asyncio
    async def test_brand_api_fallback_success(self):
        """Test successful Brand API fallback."""
        mock_domain_resp = {
            "status_code": 200,
            "candidates": ["https://example.com/some-other-logo.svg"],
            "json": {"domain": "other.com"}
        }
        mock_brand_resp = {
            "status_code": 200,
            "candidates": ["https://cdn.brandfetch.io/apple.com/logo.svg"],
            "json": [{"domain": "apple.com"}]
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_logo_api', new_callable=AsyncMock) as mock_logo_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_brand_api_search', new_callable=AsyncMock) as mock_brand_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_brand_count', return_value=0), \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.increment_brand_counter', return_value=1):
            
            mock_logo_api.return_value = mock_domain_resp
            mock_brand_api.return_value = mock_brand_resp
            
            result = await get_logo_for_domain("apple.com")
            
            assert result["logo_url"] == "https://cdn.brandfetch.io/apple.com/logo.svg"
            assert result["source"] == "brand-search"
            assert result["reason"] == "domain lookup failed or mismatch; used Brand API fallback"
            assert result["brand_api_calls_this_month"] == 1

    @pytest.mark.asyncio
    async def test_brand_api_limit_reached(self):
        """Test when Brand API limit is reached."""
        mock_domain_resp = {
            "status_code": 200,
            "candidates": ["https://example.com/some-other-logo.svg"],
            "json": {"domain": "other.com"}
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_logo_api', new_callable=AsyncMock) as mock_logo_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_brand_count', return_value=100), \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.BRAND_API_MONTH_LIMIT', 100):
            
            mock_logo_api.return_value = mock_domain_resp
            
            result = await get_logo_for_domain("apple.com")
            
            assert result["error"] == "brand_api_limit_reached"
            assert "limit reached" in result["message"]
            assert result["brand_api_calls_this_month"] == 100

    @pytest.mark.asyncio
    async def test_no_logo_found(self):
        """Test when no logo is found anywhere."""
        mock_domain_resp = {
            "status_code": 200,
            "candidates": [],
            "json": {}
        }
        mock_brand_resp = {
            "status_code": 200,
            "candidates": [],
            "json": []
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_logo_api', new_callable=AsyncMock) as mock_logo_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_brand_api_search', new_callable=AsyncMock) as mock_brand_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_brand_count', return_value=0), \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.increment_brand_counter', return_value=1):
            
            mock_logo_api.return_value = mock_domain_resp
            mock_brand_api.return_value = mock_brand_resp
            
            result = await get_logo_for_domain("nonexistent.com")
            
            assert result["error"] == "no_logo_found"
            assert "No logo candidate was found" in result["message"]
            assert result["brand_api_calls_this_month"] == 1

    @pytest.mark.asyncio
    async def test_invalid_domain(self):
        """Test with invalid domain."""
        result = await get_logo_for_domain("")
        
        assert result["error"] == "invalid_domain"
        assert "Empty domain provided" in result["message"]

    @pytest.mark.asyncio
    async def test_company_hint_parameter(self):
        """Test using company_hint parameter."""
        mock_domain_resp = {
            "status_code": 200,
            "candidates": [],
            "json": {}
        }
        mock_brand_resp = {
            "status_code": 200,
            "candidates": ["https://cdn.brandfetch.io/apple.com/logo.svg"],
            "json": [{"domain": "apple.com"}]
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_logo_api', new_callable=AsyncMock) as mock_logo_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_brand_api_search', new_callable=AsyncMock) as mock_brand_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_brand_count', return_value=0), \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.increment_brand_counter', return_value=1):
            
            mock_logo_api.return_value = mock_domain_resp
            mock_brand_api.return_value = mock_brand_resp
            
            result = await get_logo_for_domain("apple.com", company_hint="Apple Inc")
            
            assert result["logo_url"] == "https://cdn.brandfetch.io/apple.com/logo.svg"
            mock_brand_api.assert_called_once_with("Apple Inc")

    @pytest.mark.asyncio
    async def test_warning_threshold(self):
        """Test warning when approaching limit."""
        mock_domain_resp = {
            "status_code": 200,
            "candidates": ["https://example.com/some-other-logo.svg"],
            "json": {"domain": "other.com"}
        }
        mock_brand_resp = {
            "status_code": 200,
            "candidates": ["https://cdn.brandfetch.io/apple.com/logo.svg"],
            "json": [{"domain": "apple.com"}]
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_logo_api', new_callable=AsyncMock) as mock_logo_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.call_brand_api_search', new_callable=AsyncMock) as mock_brand_api, \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_brand_count', return_value=95), \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.BRAND_API_WARN_THRESHOLD', 90), \
             patch('brandfetch_mcp.brandfetch_logo_lookup_checked.increment_brand_counter', return_value=96):
            
            mock_logo_api.return_value = mock_domain_resp
            mock_brand_api.return_value = mock_brand_resp
            
            result = await get_logo_for_domain("apple.com")
            
            assert result["logo_url"] == "https://cdn.brandfetch.io/apple.com/logo.svg"
            assert result["source"] == "brand-search"
            assert "warning" in result
            assert "approaching" in result["warning"].lower()
