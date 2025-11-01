"""Comprehensive tests for Brandfetch API client."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from brandfetch_mcp.client import BrandfetchClient
import httpx


@pytest.fixture
def mock_api_key():
    """Provide a mock API key for testing."""
    return "test_api_key_12345"


@pytest.fixture
def client(mock_api_key):
    """Create a test client instance."""
    return BrandfetchClient(api_key=mock_api_key)


class TestClientInitialization:
    """Test client initialization."""

    @pytest.mark.asyncio
    async def test_client_with_api_key(self, mock_api_key):
        """Test client initializes with provided API key."""
        client = BrandfetchClient(api_key=mock_api_key)
        assert client.brand_key == mock_api_key  # api_key becomes brand_key for backward compatibility
        assert client.base_url == "https://api.brandfetch.io/v2"
        assert "Authorization" in client.brand_headers

    @pytest.mark.asyncio
    async def test_client_requires_api_key(self):
        """Test client raises error without API key."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError, match="No API keys provided"):
                BrandfetchClient()

    @pytest.mark.asyncio
    async def test_client_from_env_var(self, mock_api_key):
        """Test client reads API key from environment."""
        with patch.dict("os.environ", {"BRANDFETCH_BRAND_KEY": mock_api_key}, clear=True):
            client = BrandfetchClient()
            assert client.brand_key == mock_api_key


class TestGetBrand:
    """Test get_brand method."""

    @pytest.mark.asyncio
    async def test_get_brand_success(self, client):
        """Test successful brand data retrieval."""
        mock_response = {
            "name": "GitHub",
            "domain": "github.com",
            "logos": [],
            "colors": [],
            "fonts": []
        }

        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_response
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=mock_http_response)
            ))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            result = await client.get_brand("github.com")
            
            assert result["name"] == "GitHub"
            assert result["domain"] == "github.com"

    @pytest.mark.asyncio
    async def test_get_brand_not_found(self, client):
        """Test brand not found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Not found", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Brand not found for domain"):
                await client.get_brand("nonexistent-domain-12345.com")

    @pytest.mark.asyncio
    async def test_get_brand_401_unauthorized(self, client):
        """Test 401 unauthorized error."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Brand API authentication failed"):
                await client.get_brand("github.com")

    @pytest.mark.asyncio
    async def test_get_brand_429_rate_limit(self, client):
        """Test 429 rate limit error."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too many requests"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Too many requests", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Brand API rate limit exceeded"):
                await client.get_brand("github.com")

    @pytest.mark.asyncio
    async def test_get_brand_generic_http_error(self, client):
        """Test generic HTTP error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Internal Server Error", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="API error 500"):
                await client.get_brand("github.com")

    @pytest.mark.asyncio
    async def test_get_brand_timeout(self, client):
        """Test timeout error."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Request timeout"):
                await client.get_brand("github.com")


class TestSearchBrands:
    """Test search_brands method."""

    @pytest.mark.asyncio
    async def test_search_brands_success(self, client):
        """Test successful brand search."""
        mock_results = [
            {"name": "GitHub", "domain": "github.com"},
            {"name": "GitLab", "domain": "gitlab.com"}
        ]

        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_results
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=mock_http_response)
            ))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            result = await client.search_brands("git", limit=2)
            
            assert len(result) == 2
            assert result[0]["name"] == "GitHub"

    @pytest.mark.asyncio
    async def test_search_brands_with_limit(self, client):
        """Test search respects limit parameter."""
        mock_results = [{"name": f"Brand{i}", "domain": f"brand{i}.com"} for i in range(10)]

        mock_http_response = MagicMock()
        mock_http_response.json.return_value = mock_results
        mock_http_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(
                get=AsyncMock(return_value=mock_http_response)
            ))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            result = await client.search_brands("brand", limit=5)
            
            assert len(result) == 5

    @pytest.mark.asyncio
    async def test_search_brands_401_unauthorized(self, client):
        """Test 401 unauthorized error during search."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Unauthorized", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Brand API authentication failed"):
                await client.search_brands("coffee")

    @pytest.mark.asyncio
    async def test_search_brands_429_rate_limit(self, client):
        """Test 429 rate limit error during search."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too many requests"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Too many requests", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Brand API rate limit exceeded"):
                await client.search_brands("coffee")

    @pytest.mark.asyncio
    async def test_search_brands_generic_http_error(self, client):
        """Test generic HTTP error during search."""
        mock_response = MagicMock()
        mock_response.status_code = 502
        mock_response.text = "Bad Gateway"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.HTTPStatusError(
                "Bad Gateway", request=MagicMock(), response=mock_response
            ))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="API error 502"):
                await client.search_brands("coffee")

    @pytest.mark.asyncio
    async def test_search_brands_timeout(self, client):
        """Test timeout error during search."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_context = MagicMock()
            mock_get = AsyncMock(side_effect=httpx.TimeoutException("Request timeout"))
            mock_context.__aenter__ = AsyncMock(return_value=MagicMock(get=mock_get))
            mock_context.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_context

            with pytest.raises(ValueError, match="Request timeout"):
                await client.search_brands("coffee")


class TestGetBrandLogo:
    """Test get_brand_logo method."""

    @pytest.mark.asyncio
    async def test_get_brand_logo_success(self, client):
        """Test successful logo retrieval."""
        mock_brand_data = {
            "logos": [
                {
                    "type": "logo",
                    "theme": "light",
                    "formats": [
                        {"format": "svg", "src": "https://example.com/logo.svg"}
                    ]
                }
            ]
        }

        with patch.object(client, "get_brand", return_value=mock_brand_data):
            result = await client.get_brand_logo("example.com", format="svg")
            
            assert result["url"] == "https://example.com/logo.svg"
            assert result["format"] == "svg"

    @pytest.mark.asyncio
    async def test_get_brand_logo_no_logos(self, client):
        """Test error when no logos available."""
        mock_brand_data = {"logos": []}

        with patch.object(client, "get_brand", return_value=mock_brand_data):
            with pytest.raises(ValueError, match="No logos found"):
                await client.get_brand_logo("example.com")

    @pytest.mark.asyncio
    async def test_get_brand_logo_fallback_first_available(self, client):
        """Test fallback to first available logo when requested format/theme/type not found."""
        mock_brand_data = {
            "logos": [
                {
                    "type": "icon",
                    "theme": "dark",
                    "formats": [
                        {"format": "png", "src": "https://example.com/icon-dark.png"}
                    ]
                }
            ]
        }

        with patch.object(client, "get_brand", return_value=mock_brand_data):
            result = await client.get_brand_logo("example.com", format="svg", theme="light", logo_type="logo")

            assert result["url"] == "https://example.com/icon-dark.png"
            assert result["format"] == "png"
            assert result["theme"] == "dark"
            assert result["type"] == "icon"
            assert "Requested format (svg, light, logo) not found" in result["note"]


class TestGetBrandColors:
    """Test get_brand_colors method."""

    @pytest.mark.asyncio
    async def test_get_brand_colors_success(self, client):
        """Test successful color extraction."""
        mock_brand_data = {
            "colors": [
                {"hex": "#FF0000", "type": "primary"},
                {"hex": "#00FF00", "type": "secondary"}
            ]
        }

        with patch.object(client, "get_brand", return_value=mock_brand_data):
            result = await client.get_brand_colors("example.com")
            
            assert len(result) == 2
            assert result[0]["hex"] == "#FF0000"

    @pytest.mark.asyncio
    async def test_get_brand_colors_no_colors(self, client):
        """Test error when no colors available."""
        mock_brand_data = {"colors": []}

        with patch.object(client, "get_brand", return_value=mock_brand_data):
            with pytest.raises(ValueError, match="No colors found"):
                await client.get_brand_colors("example.com")
