import pytest
import os
import httpx
from unittest.mock import patch
import respx
from dotenv import load_dotenv
from brandfetch_mcp.client import BrandfetchClient


# Ensure environment variables from .env are loaded before tests evaluate skip conditions
load_dotenv()


class TestBrandfetchClientInit:
    """Test client initialization and API key validation."""
    
    def test_init_success(self):
        """Test successful client initialization with valid API key."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            assert client.api_key == "test_key"
            assert client.base_url == "https://api.brandfetch.io/v2"
            assert "Authorization" in client.headers
            assert client.headers["Authorization"] == "Bearer test_key"
    
    def test_init_with_client_id(self):
        """Test initialization with client ID."""
        with patch.dict(os.environ, {
            "BRANDFETCH_API_KEY": "test_key",
            "BRANDFETCH_CLIENT_ID": "test_client_id"
        }):
            client = BrandfetchClient()
            assert client.client_id == "test_client_id"
    
    def test_init_missing_api_key(self):
        """Test initialization fails without API key."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="BRANDFETCH_API_KEY must be set"):
                BrandfetchClient()
    
    def test_init_empty_api_key(self):
        """Test initialization fails with empty API key."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": ""}):
            with pytest.raises(ValueError, match="BRANDFETCH_API_KEY must be set"):
                BrandfetchClient()


class TestAppendClientId:
    """Test client ID URL appending functionality."""
    
    def test_append_client_id_no_client_id(self):
        """Test URL unchanged when no client ID is set."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            client.client_id = None
            
            url = "https://cdn.brandfetch.io/test.png"
            result = client._append_client_id(url)
            assert result == url
    
    def test_append_client_id_non_cdn_url(self):
        """Test non-CDN URLs are unchanged."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            client.client_id = "test_client"
            
            url = "https://example.com/image.png"
            result = client._append_client_id(url)
            assert result == url
    
    def test_append_client_id_cdn_url_no_query(self):
        """Test appending client ID to CDN URL without existing query."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            client.client_id = "test_client"
            
            url = "https://cdn.brandfetch.io/test.png"
            result = client._append_client_id(url)
            assert result == "https://cdn.brandfetch.io/test.png?c=test_client"
    
    def test_append_client_id_cdn_url_with_existing_query(self):
        """Test appending client ID to CDN URL with existing query params."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            client.client_id = "test_client"
            
            url = "https://cdn.brandfetch.io/test.png?foo=bar&size=large"
            result = client._append_client_id(url)
            
            # Should preserve existing params and add client ID
            assert "foo=bar" in result
            assert "size=large" in result
            assert "c=test_client" in result
    
    def test_append_client_id_cdn_url_replaces_existing_c(self):
        """Test that existing 'c' parameter is replaced with client ID."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            client.client_id = "new_client"
            
            url = "https://cdn.brandfetch.io/test.png?c=old_client&foo=bar"
            result = client._append_client_id(url)
            
            # Should replace existing c parameter
            assert "c=new_client" in result
            assert "c=old_client" not in result
            assert "foo=bar" in result


class TestGetBrand:
    """Test get_brand method functionality."""
    
    @respx.mock
    async def test_get_brand_success(self):
        """Test successful brand retrieval."""
        mock_response = {
            "name": "GitHub",
            "domain": "github.com",
            "description": "Development platform",
            "logos": [],
            "colors": []
        }
        
        respx.get("https://api.brandfetch.io/v2/brands/github.com").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand("github.com")
            
            assert result["name"] == "GitHub"
            assert result["domain"] == "github.com"
    
    @respx.mock
    async def test_get_brand_domain_cleaning(self):
        """Test domain cleaning for various input formats."""
        mock_response = {"name": "Test", "domain": "test.com"}
        
        # Mock all possible cleaned domains
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            # Test various domain formats
            test_cases = [
                "https://test.com",
                "http://test.com",
                "https://www.test.com",
                "http://www.test.com",
                "test.com/",
                "https://www.test.com/",
                "www.test.com"
            ]
            
            for domain in test_cases:
                result = await client.get_brand(domain)
                assert result["name"] == "Test"
    
    @respx.mock
    async def test_get_brand_http_errors(self):
        """Test HTTP error handling."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            # Test 404 error
            respx.get("https://api.brandfetch.io/v2/brands/notfound.com").mock(
                return_value=httpx.Response(404, json={"error": "Not found"})
            )
            
            with pytest.raises(ValueError, match="Brand not found for domain: notfound.com"):
                await client.get_brand("notfound.com")
            
            # Test 401 error
            respx.get("https://api.brandfetch.io/v2/brands/unauthorized.com").mock(
                return_value=httpx.Response(401, json={"error": "Unauthorized"})
            )
            
            with pytest.raises(ValueError, match="Invalid API key. Check BRANDFETCH_API_KEY."):
                await client.get_brand("unauthorized.com")
            
            # Test 429 rate limit
            respx.get("https://api.brandfetch.io/v2/brands/ratelimited.com").mock(
                return_value=httpx.Response(429, json={"error": "Rate limit exceeded"})
            )
            
            with pytest.raises(ValueError, match="Rate limit exceeded. Try again later."):
                await client.get_brand("ratelimited.com")
    
    @respx.mock
    async def test_get_brand_timeout(self):
        """Test timeout handling."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            # Mock timeout
            respx.get("https://api.brandfetch.io/v2/brands/slow.com").mock(
                side_effect=httpx.TimeoutException("Request timeout")
            )
            
            with pytest.raises(ValueError, match="Request timeout for domain: slow.com"):
                await client.get_brand("slow.com")


class TestSearchBrands:
    """Test search_brands method functionality."""
    
    @respx.mock
    async def test_search_brands_success(self):
        """Test successful brand search."""
        mock_response = [
            {"name": "GitHub", "domain": "github.com"},
            {"name": "GitLab", "domain": "gitlab.com"}
        ]
        
        respx.get("https://api.brandfetch.io/v2/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.search_brands("git", limit=5)
            
            assert len(result) == 2
            assert result[0]["name"] == "GitHub"
    
    @respx.mock
    async def test_search_brands_limit_validation(self):
        """Test limit parameter handling."""
        mock_response = [{"name": "Test", "domain": "test.com"}]
        
        respx.get("https://api.brandfetch.io/v2/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            # Test limit > 50 gets capped
            await client.search_brands("test", limit=100)
            
            # Verify the request was made with limit=50
            request = respx.calls.last.request
            assert "limit=50" in str(request.url)
    
    @respx.mock
    async def test_search_brands_default_limit(self):
        """Test default limit is applied."""
        mock_response = [{"name": "Test", "domain": "test.com"}]
        
        respx.get("https://api.brandfetch.io/v2/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            await client.search_brands("test")  # No limit specified
            
            # Verify the request was made with limit=10 (default)
            request = respx.calls.last.request
            assert "limit=10" in str(request.url)
    
    @respx.mock
    async def test_search_brands_query_encoding(self):
        """Test query parameter encoding."""
        mock_response = []
        
        respx.get("https://api.brandfetch.io/v2/search").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            await client.search_brands("coffee & tea")
            
            # Verify query is properly encoded
            request = respx.calls.last.request
            assert "q=coffee+%26+tea" in str(request.url)


class TestGetBrandLogo:
    """Test get_brand_logo method functionality."""
    
    @pytest.fixture
    def mock_brand_data(self):
        """Fixture providing comprehensive mock brand data."""
        return {
            "name": "TestBrand",
            "domain": "test.com",
            "logos": [
                {
                    "type": "logo",
                    "theme": "light",
                    "formats": [
                        {"format": "svg", "src": "https://cdn.brandfetch.io/light.svg"},
                        {"format": "png", "src": "https://cdn.brandfetch.io/light.png"}
                    ]
                },
                {
                    "type": "logo",
                    "theme": "dark",
                    "formats": [
                        {"format": "svg", "src": "https://cdn.brandfetch.io/dark.svg"},
                        {"format": "png", "src": "https://cdn.brandfetch.io/dark.png"}
                    ]
                },
                {
                    "type": "icon",
                    "theme": "light",
                    "formats": [
                        {"format": "svg", "src": "https://cdn.brandfetch.io/icon.svg"}
                    ]
                }
            ]
        }
    
    @respx.mock
    async def test_get_brand_logo_exact_match(self, mock_brand_data):
        """Test logo selection with exact format/theme/type match."""
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand_logo("test.com", format="svg", theme="dark", type="logo")
            
            assert result["format"] == "svg"
            assert result["theme"] == "dark"
            assert result["type"] == "logo"
            assert "dark.svg" in result["url"]
    
    @respx.mock
    async def test_get_brand_logo_fallback_to_type_match(self, mock_brand_data):
        """Test logo selection falls back to type match when theme not found."""
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            # Request non-existent theme, should fall back to any logo type
            result = await client.get_brand_logo("test.com", format="svg", theme="purple", type="logo")
            
            assert result["type"] == "logo"
            assert result["format"] == "svg"
    
    @respx.mock
    async def test_get_brand_logo_fallback_to_any_logo(self, mock_brand_data):
        """Test logo selection falls back to any logo when type not found."""
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            # Request non-existent type, should fall back to any logo
            result = await client.get_brand_logo("test.com", format="svg", theme="light", type="nonexistent")
            
            assert result["url"] is not None
    
    @respx.mock
    async def test_get_brand_logo_format_fallback(self, mock_brand_data):
        """Test format fallback when preferred format not available."""
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            # Request non-existent format, should fall back to first available
            result = await client.get_brand_logo("test.com", format="webp", theme="light", type="logo")
            
            assert result["format"] in ["svg", "png"]
    
    @respx.mock
    async def test_get_brand_logo_no_logos(self):
        """Test error when no logos are available."""
        mock_brand_data = {
            "name": "TestBrand",
            "domain": "test.com",
            "logos": []  # Empty logos array
        }
        
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            with pytest.raises(ValueError, match="No logo found"):
                await client.get_brand_logo("test.com")
    
    @respx.mock
    async def test_get_brand_logo_with_client_id(self, mock_brand_data):
        """Test client ID is appended to logo URLs."""
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {
            "BRANDFETCH_API_KEY": "test_key",
            "BRANDFETCH_CLIENT_ID": "test_client"
        }):
            client = BrandfetchClient()
            result = await client.get_brand_logo("test.com", format="svg", theme="light", type="logo")
            
            assert "c=test_client" in result["url"]
    
    @respx.mock
    async def test_get_brand_logo_metadata(self, mock_brand_data):
        """Test logo metadata is properly extracted."""
        enhanced_mock_data = mock_brand_data.copy()
        enhanced_mock_data["logos"][0]["formats"][0].update({
            "size": 1024,
            "width": 100,
            "height": 50
        })
        enhanced_mock_data["logos"][0]["background"] = "#ffffff"
        
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=enhanced_mock_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand_logo("test.com")
            
            metadata = result["metadata"]
            assert metadata["size"] == 1024
            assert metadata["width"] == 100
            assert metadata["height"] == 50
            assert metadata["background"] == "#ffffff"


class TestGetBrandColors:
    """Test get_brand_colors method functionality."""
    
    @respx.mock
    async def test_get_brand_colors_success(self):
        """Test successful color extraction."""
        mock_brand_data = {
            "name": "TestBrand",
            "domain": "test.com",
            "colors": [
                {"hex": "#FF0000", "type": "primary", "brightness": "light"},
                {"hex": "#00FF00", "type": "secondary", "brightness": "dark"},
                {"hex": "#0000FF", "type": "accent"}  # Missing brightness
            ]
        }
        
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand_colors("test.com")
            
            assert len(result) == 3
            assert result[0]["hex"] == "#FF0000"
            assert result[0]["type"] == "primary"
            assert result[0]["brightness"] == "light"
            
            # Test default values
            assert result[2]["type"] == "accent"
            assert result[2]["brightness"] == "unknown"
    
    @respx.mock
    async def test_get_brand_colors_empty_colors(self):
        """Test handling of empty colors array."""
        mock_brand_data = {
            "name": "TestBrand",
            "domain": "test.com",
            "colors": []
        }
        
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand_colors("test.com")
            
            assert result == []
    
    @respx.mock
    async def test_get_brand_colors_missing_colors_field(self):
        """Test handling of missing colors field."""
        mock_brand_data = {
            "name": "TestBrand",
            "domain": "test.com"
            # No colors field
        }
        
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_brand_data)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand_colors("test.com")
            
            assert result == []


class TestDomainCleaning:
    """Test domain cleaning logic used across multiple methods."""
    
    @respx.mock
    async def test_domain_cleaning_comprehensive(self):
        """Test comprehensive domain cleaning edge cases."""
        mock_response = {"name": "Test", "domain": "test.com"}
        
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json=mock_response)
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            # Test comprehensive edge cases
            test_cases = [
                ("https://www.test.com/", "test.com"),
                ("http://www.test.com/path", "test.com"),
                ("https://test.com/path/to/page", "test.com"),
                ("www.test.com", "test.com"),
                ("test.com", "test.com"),
                ("HTTPS://WWW.TEST.COM/", "test.com"),  # Case insensitive - note: client doesn't lowercase
                ("   test.com   ", "test.com"),  # Whitespace
            ]
            
            for input_domain, expected_clean in test_cases:
                # Test that all result in the same cleaned domain
                result = await client.get_brand(input_domain)
                assert result["domain"] == "test.com"


@pytest.mark.integration
class TestIntegration:
    """Integration tests that make real API calls (requires valid credentials)."""
    
    async def test_real_api_call_get_brand(self):
        """Test real API call for get_brand (requires valid API key)."""
        api_key = os.getenv("BRANDFETCH_API_KEY")
        if not api_key or api_key == "paste_brand_key_here":
            pytest.fail("BRANDFETCH_API_KEY must be set to a real value for integration tests")
        
        client = BrandfetchClient()
        try:
            result = await client.get_brand("github.com")
        finally:
            await client.close()

        assert "name" in result
        assert "domain" in result
        assert result["domain"] == "github.com"
        assert isinstance(result.get("logos"), list)
        assert isinstance(result.get("colors"), list)
    
    async def test_real_api_call_search_brands(self):
        """Test real API call for search_brands (requires valid API key)."""
        api_key = os.getenv("BRANDFETCH_API_KEY")
        if not api_key or api_key == "paste_brand_key_here":
            pytest.fail("BRANDFETCH_API_KEY must be set to a real value for integration tests")

        client = BrandfetchClient()
        try:
            results = await client.search_brands("coffee", limit=3)
            
            assert isinstance(results, list)
            assert len(results) <= 3
            if results:
                assert "name" in results[0]
                assert "domain" in results[0]
        except ValueError as e:
            assert "Brandfetch Pro subscription" in str(e)
        finally:
            await client.close()


class TestEdgeCases:
    """Test additional edge cases and error conditions."""
    
    def test_client_isolation(self):
        """Test that multiple client instances don't interfere."""
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "key1"}):
            client1 = BrandfetchClient()
            assert client1.api_key == "key1"
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "key2"}):
            client2 = BrandfetchClient()
            assert client2.api_key == "key2"
        
        # Original client should still have its original key
        assert client1.api_key == "key1"
    
    @respx.mock
    async def test_malformed_api_response(self):
        """Test handling of malformed API responses."""
        # Test non-JSON response
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, text="not json")
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            
            with pytest.raises(Exception):  # httpx may raise various exceptions for invalid JSON
                await client.get_brand("test.com")
    
    @respx.mock
    async def test_empty_api_response(self):
        """Test handling of empty API response."""
        respx.get("https://api.brandfetch.io/v2/brands/test.com").mock(
            return_value=httpx.Response(200, json={})
        )
        
        with patch.dict(os.environ, {"BRANDFETCH_API_KEY": "test_key"}):
            client = BrandfetchClient()
            result = await client.get_brand("test.com")
            
            # Should handle empty response gracefully
            assert isinstance(result, dict)
            assert len(result) == 0