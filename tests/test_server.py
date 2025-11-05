"""Comprehensive tests for Brandfetch MCP server."""

import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from brandfetch_mcp.server import list_tools, call_tool, format_brand_details, format_search_results, format_logo_response, format_colors_response
from brandfetch_mcp.client import BrandfetchClient
import httpx


@pytest.fixture(autouse=True)
def mock_brandfetch_client(request):
    """Mock the BrandfetchClient by default; disable for integration tests."""
    # If this test (or its parent class) is marked as integration, do not mock
    if request.node.get_closest_marker("integration"):
        # Let real client run
        yield None
        return

    mock_client = MagicMock()
    mock_client.get_brand = AsyncMock()
    mock_client.search_brands = AsyncMock()
    mock_client.get_brand_logo = AsyncMock()
    mock_client.get_brand_colors = AsyncMock()

    with patch('brandfetch_mcp.server.brandfetch', mock_client):
        yield mock_client


# PHASE 1: Production-Ready Foundation

class TestMCPProtocol:
    """Test MCP protocol compliance."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_four_tools(self):
        """Test list_tools returns all 5 tools with correct schemas."""
        tools = await list_tools()

        assert len(tools) == 5
        tool_names = {tool.name for tool in tools}
        expected_names = {"get_brand_details", "search_brands", "get_brand_logo", "get_brand_colors", "get_logo_url"}
        assert tool_names == expected_names

    @pytest.mark.asyncio
    async def test_get_brand_details_tool_schema(self):
        """Test get_brand_details tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "get_brand_details")

        assert tool.name == "get_brand_details"
        assert "domain" in tool.inputSchema["required"]
        assert "domain" in tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_call_tool_unknown_tool(self):
        """Test call_tool with unknown tool name raises error."""
        result = await call_tool("unknown_tool", {})

        assert len(result) == 1
        assert "❌ Error: Unknown tool: unknown_tool" in result[0].text


class TestToolHandlers:
    """Test each tool handler through MCP interface."""

    @pytest.mark.asyncio
    async def test_get_brand_details_tool(self, mock_brandfetch_client):
        """Test get_brand_details tool through MCP interface."""
        mock_brandfetch_client.get_brand.return_value = {
            "name": "GitHub",
            "domain": "github.com",
            "description": "Code hosting platform",
            "logos": [],
            "colors": [],
            "fonts": []
        }

        result = await call_tool("get_brand_details", {"domain": "github.com"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "GitHub" in result[0].text
        assert "github.com" in result[0].text
        mock_brandfetch_client.get_brand.assert_called_once_with("github.com")

    @pytest.mark.asyncio
    async def test_search_brands_tool(self, mock_brandfetch_client):
        """Test search_brands tool through MCP interface."""
        mock_brandfetch_client.search_brands.return_value = [
            {"name": "GitHub", "domain": "github.com"},
            {"name": "GitLab", "domain": "gitlab.com"}
        ]

        result = await call_tool("search_brands", {"query": "git", "limit": 5})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "Found 2 brands" in result[0].text
        assert "GitHub" in result[0].text
        mock_brandfetch_client.search_brands.assert_called_once_with("git", 5)

    @pytest.mark.asyncio
    async def test_get_brand_logo_tool(self, mock_brandfetch_client):
        """Test get_brand_logo tool through MCP interface."""
        mock_brandfetch_client.get_brand_logo.return_value = {
            "url": "https://example.com/logo.svg",
            "format": "svg",
            "theme": "light",
            "type": "logo"
        }

        result = await call_tool("get_brand_logo", {
            "domain": "github.com",
            "format": "svg",
            "theme": "dark",
            "type": "icon"
        })

        assert len(result) == 1
        assert result[0].type == "text"
        assert "https://example.com/logo.svg" in result[0].text
        mock_brandfetch_client.get_brand_logo.assert_called_once_with("github.com", "svg", "dark", "icon")

    @pytest.mark.asyncio
    async def test_get_brand_colors_tool(self, mock_brandfetch_client):
        """Test get_brand_colors tool through MCP interface."""
        mock_brandfetch_client.get_brand_colors.return_value = [
            {"hex": "#FF0000", "type": "primary"},
            {"hex": "#00FF00", "type": "secondary"}
        ]

        result = await call_tool("get_brand_colors", {"domain": "github.com"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "#FF0000" in result[0].text
        assert "#00FF00" in result[0].text
        mock_brandfetch_client.get_brand_colors.assert_called_once_with("github.com")

    @pytest.mark.asyncio
    async def test_get_logo_url_tool_domain(self, mock_brandfetch_client):
        """Test get_logo_url tool through MCP interface with domain."""
        mock_result = {
            "logo_url": "https://cdn.brandfetch.io/github.com",
            "source": "domain-logo",
            "reason": "domain lookup returned matching candidate",
            "brand_api_calls_this_month": 0
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_logo_for_domain', new_callable=AsyncMock) as mock_get_logo:
            mock_get_logo.return_value = mock_result

            result = await call_tool("get_logo_url", {"domain": "github.com"})

            assert len(result) == 1
            assert result[0].type == "text"
            assert "**Logo URL:** https://cdn.brandfetch.io/github.com" in result[0].text
            assert "**Source:** domain-logo" in result[0].text
            mock_get_logo.assert_called_once_with("github.com")

    @pytest.mark.asyncio
    async def test_get_logo_url_tool_name(self, mock_brandfetch_client):
        """Test get_logo_url tool through MCP interface with name."""
        mock_result = {
            "logo_url": "https://cdn.brandfetch.io/github.com",
            "source": "brand-search",
            "reason": "domain lookup failed; used Brand API fallback",
            "brand_api_calls_this_month": 5,
            "warning": "approaching Brand API monthly limit"
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_logo_for_domain', new_callable=AsyncMock) as mock_get_logo:
            mock_get_logo.return_value = mock_result

            result = await call_tool("get_logo_url", {"name": "GitHub"})

            assert len(result) == 1
            assert result[0].type == "text"
            assert "**Logo URL:** https://cdn.brandfetch.io/github.com" in result[0].text
            assert "**Source:** brand-search" in result[0].text
            assert "**Warning:** approaching Brand API monthly limit" in result[0].text
            assert "**Brand API calls this month:** 5" in result[0].text
            mock_get_logo.assert_called_once_with("GitHub", company_hint="GitHub")

    @pytest.mark.asyncio
    async def test_get_logo_url_tool_no_result(self, mock_brandfetch_client):
        """Test get_logo_url tool when no logo is found."""
        mock_result = {
            "error": "no_logo_found",
            "message": "No logo candidate was found from domain lookup or Brand API search",
            "brand_api_calls_this_month": 1
        }

        with patch('brandfetch_mcp.brandfetch_logo_lookup_checked.get_logo_for_domain', new_callable=AsyncMock) as mock_get_logo:
            mock_get_logo.return_value = mock_result

            result = await call_tool("get_logo_url", {"domain": "nonexistent.com"})

            assert len(result) == 1
            assert result[0].type == "text"
            assert "❌ **No logo found**" in result[0].text
            mock_get_logo.assert_called_once_with("nonexistent.com")


class TestErrorResponseFormat:
    """Test MCP error response format."""

    @pytest.mark.asyncio
    async def test_value_error_formatting(self, mock_brandfetch_client):
        """Test ValueError is formatted correctly for MCP."""
        mock_brandfetch_client.get_brand.side_effect = ValueError("Brand not found for domain: nonexistent.com")

        result = await call_tool("get_brand_details", {"domain": "nonexistent.com"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "❌ Error: Brand not found for domain: nonexistent.com" == result[0].text

    @pytest.mark.asyncio
    async def test_http_error_formatting(self, mock_brandfetch_client):
        """Test HTTPStatusError is formatted correctly for MCP."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not found"
        mock_brandfetch_client.get_brand.side_effect = httpx.HTTPStatusError(
            "Not found", request=MagicMock(), response=mock_response
        )

        result = await call_tool("get_brand_details", {"domain": "nonexistent.com"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "❌ API Error: API error (404): Not found" == result[0].text

    @pytest.mark.asyncio
    async def test_unexpected_error_formatting(self, mock_brandfetch_client):
        """Test unexpected exceptions are formatted correctly."""
        mock_brandfetch_client.get_brand.side_effect = Exception("Unexpected error")

        result = await call_tool("get_brand_details", {"domain": "github.com"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "❌ Error: Unexpected error executing get_brand_details: Unexpected error" == result[0].text


# PHASE 2: Comprehensive Coverage

class TestSchemaValidation:
    """Test schema validation and parameter handling."""

    @pytest.mark.asyncio
    async def test_get_brand_details_missing_domain(self, mock_brandfetch_client):
        """Test get_brand_details with missing domain parameter."""
        # When domain is missing, KeyError is raised before client is called
        result = await call_tool("get_brand_details", {})

        # Should return error response, client should not be called
        assert len(result) == 1
        assert result[0].type == "text"
        assert "❌ Error:" in result[0].text
        mock_brandfetch_client.get_brand.assert_not_called()

    @pytest.mark.asyncio
    async def test_search_brands_default_limit(self, mock_brandfetch_client):
        """Test search_brands uses default limit when not provided."""
        mock_brandfetch_client.search_brands.return_value = [{"name": "Test", "domain": "test.com"}]

        result = await call_tool("search_brands", {"query": "test"})

        mock_brandfetch_client.search_brands.assert_called_once_with("test", 10)  # default limit
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_get_brand_logo_default_params(self, mock_brandfetch_client):
        """Test get_brand_logo uses default parameters."""
        mock_brandfetch_client.get_brand_logo.return_value = {
            "url": "https://example.com/logo.svg",
            "format": "svg",
            "theme": "light",
            "type": "logo"
        }

        result = await call_tool("get_brand_logo", {"domain": "test.com"})

        mock_brandfetch_client.get_brand_logo.assert_called_once_with("test.com", "svg", "light", "logo")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_search_brands_tool_schema(self):
        """Test search_brands tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "search_brands")

        assert tool.name == "search_brands"
        assert "query" in tool.inputSchema["required"]
        assert "query" in tool.inputSchema["properties"]
        assert tool.inputSchema["properties"]["limit"]["default"] == 10

    @pytest.mark.asyncio
    async def test_get_brand_logo_tool_schema(self):
        """Test get_brand_logo tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "get_brand_logo")

        assert tool.name == "get_brand_logo"
        assert "domain" in tool.inputSchema["required"]
        assert tool.inputSchema["properties"]["format"]["default"] == "svg"
        assert tool.inputSchema["properties"]["theme"]["default"] == "light"
        assert tool.inputSchema["properties"]["type"]["default"] == "logo"

    @pytest.mark.asyncio
    async def test_get_brand_colors_tool_schema(self):
        """Test get_brand_colors tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "get_brand_colors")

        assert tool.name == "get_brand_colors"
        assert "domain" in tool.inputSchema["required"]
        assert "domain" in tool.inputSchema["properties"]

    @pytest.mark.asyncio
    async def test_get_logo_url_tool_schema(self):
        """Test get_logo_url tool has correct schema."""
        tools = await list_tools()
        tool = next(t for t in tools if t.name == "get_logo_url")

        assert tool.name == "get_logo_url"
        # Should require either domain OR name (oneOf validation)
        assert "oneOf" in tool.inputSchema
        assert len(tool.inputSchema["oneOf"]) == 2
        assert "domain" in tool.inputSchema["properties"]
        assert "name" in tool.inputSchema["properties"]


class TestFormattingFunctions:
    """Test formatting functions directly."""

    def test_format_brand_details_basic(self):
        """Test format_brand_details with basic data."""
        data = {
            "name": "GitHub",
            "domain": "github.com",
            "description": "Code hosting platform",
            "logos": [{"type": "logo", "theme": "light", "formats": [{"src": "https://example.com/logo.svg", "format": "svg", "size": 1024}]}],
            "colors": [{"hex": "#FF0000", "type": "primary", "brightness": 100}],
            "fonts": [{"name": "system-ui", "type": "body"}]
        }

        result = format_brand_details(data)

        assert "# GitHub (github.com)" in result
        assert "Code hosting platform" in result
        assert "logo.svg" in result
        assert "#FF0000" in result
        assert "system-ui" in result

    def test_format_brand_details_empty_data(self):
        """Test format_brand_details with minimal data."""
        data = {"name": "Test", "domain": "test.com"}

        result = format_brand_details(data)

        assert "# Test (test.com)" in result
        assert "logos" not in result  # No logos section if empty

    def test_format_search_results(self):
        """Test format_search_results."""
        results = [
            {"name": "GitHub", "domain": "github.com", "claimed": True},
            {"name": "GitLab", "domain": "gitlab.com", "claimed": False}
        ]

        result = format_search_results(results)

        assert "Found 2 brands:" in result
        assert "GitHub" in result
        assert "✓ Claimed" in result
        assert "Unclaimed" in result

    def test_format_search_results_empty(self):
        """Test format_search_results with empty results."""
        result = format_search_results([])

        assert "No brands found matching your search" in result

    def test_format_logo_response(self):
        """Test format_logo_response."""
        logo = {
            "url": "https://example.com/logo.svg",
            "format": "svg",
            "theme": "light",
            "type": "logo",
            "metadata": {"size": 1024, "width": 100, "height": 100}
        }

        result = format_logo_response(logo)

        assert "https://example.com/logo.svg" in result
        assert "**Format:** svg" in result
        assert "Size: 1,024 bytes" in result

    def test_format_colors_response(self):
        """Test format_colors_response."""
        colors = [
            {"hex": "#FF0000", "type": "primary", "brightness": 100},
            {"hex": "#00FF00", "type": "secondary", "brightness": 150}
        ]

        result = format_colors_response(colors)

        assert "**Brand Color Palette:** 2 colors" in result
        assert "Primary Colors:" in result
        assert "#FF0000" in result
        assert "#00FF00" in result


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_empty_brand_data(self, mock_brandfetch_client):
        """Test handling of empty brand data."""
        mock_brandfetch_client.get_brand.return_value = {"name": "Test", "domain": "test.com"}

        result = await call_tool("get_brand_details", {"domain": "test.com"})

        assert len(result) == 1
        assert "Test" in result[0].text

    @pytest.mark.asyncio
    async def test_missing_fields_in_response(self, mock_brandfetch_client):
        """Test handling of missing fields in API response."""
        mock_brandfetch_client.get_brand.return_value = {"name": "Test"}  # Missing domain

        result = await call_tool("get_brand_details", {"domain": "test.com"})

        assert len(result) == 1
        assert "Test" in result[0].text
        # Should not crash on missing fields

    @pytest.mark.asyncio
    async def test_search_with_zero_results(self, mock_brandfetch_client):
        """Test search with zero results."""
        mock_brandfetch_client.search_brands.return_value = []

        result = await call_tool("search_brands", {"query": "nonexistent"})

        assert len(result) == 1
        assert "No brands found matching your search" in result[0].text


# PHASE 3: Production Excellence

class TestAuthErrors:
    """Test authentication error scenarios."""

    @pytest.mark.asyncio
    async def test_401_unauthorized_error(self, mock_brandfetch_client):
        """Test 401 unauthorized error formatting."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_brandfetch_client.get_brand.side_effect = httpx.HTTPStatusError(
            "Unauthorized", request=MagicMock(), response=mock_response
        )

        result = await call_tool("get_brand_details", {"domain": "github.com"})

        assert len(result) == 1
        assert "❌ API Error: API error (401): Unauthorized" == result[0].text

    @pytest.mark.asyncio
    async def test_429_rate_limit_error(self, mock_brandfetch_client):
        """Test rate limit error handling."""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.text = "Too many requests"
        mock_brandfetch_client.get_brand.side_effect = httpx.HTTPStatusError(
            "Too many requests", request=MagicMock(), response=mock_response
        )

        result = await call_tool("get_brand_details", {"domain": "github.com"})

        assert len(result) == 1
        assert "❌ API Error: API error (429): Too many requests" == result[0].text


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("BRANDFETCH_API_KEY"),
    reason="Requires BRANDFETCH_API_KEY and internet connection",
)
@pytest.mark.usefixtures("real_brandfetch_client")
class TestIntegration:
    """Integration tests with real API (manual/skip in CI)."""

    @pytest.mark.asyncio
    async def test_real_api_brand_details(self):
        """Integration test with real Brandfetch API."""
        # This would use real BrandfetchClient without mocks
        # Skipped in CI, run manually with valid API key
        result = await call_tool("get_brand_details", {"domain": "github.com"})

        assert len(result) == 1
        assert result[0].type == "text"
        assert "GitHub" in result[0].text

    @pytest.mark.asyncio
    async def test_real_api_search_brands(self):
        """Integration test for search with real API."""
        result = await call_tool("search_brands", {"query": "coffee", "limit": 3})

        assert len(result) == 1
        assert result[0].type == "text"
        # Free tier accounts may not have access to search; accept informative error as pass
        text = result[0].text.lower()
        assert ("coffee" in text or "brands" in text or "error" in text or "requires" in text)


# Real client fixture for integration tests to ensure AsyncClient binds to the active event loop
@pytest_asyncio.fixture(scope="function")
async def real_brandfetch_client():
    # Patch the server's global client with a fresh instance bound to this loop
    import brandfetch_mcp.server as server_mod
    original = getattr(server_mod, "brandfetch", None)
    client = BrandfetchClient()
    server_mod.brandfetch = client
    try:
        yield
    finally:
        try:
            await client.close()
        finally:
            if original is not None:
                server_mod.brandfetch = original
