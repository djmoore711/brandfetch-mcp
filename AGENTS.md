# AI Agent Instructions for Brandfetch MCP Server

## Project Overview

You are completing a Model Context Protocol (MCP) server that integrates with the Brandfetch API. This server allows AI assistants like Claude to retrieve brand data including logos, colors, fonts, and company information.

**Key Facts:**
- Language: Python 3.10+
- Framework: MCP Python SDK
- API: Brandfetch REST API (https://api.brandfetch.io/v2/)
- Transport: stdio (standard input/output)
- Purpose: AI model testing and prompt development

## Current Implementation Status

### ✅ Complete
- Project structure and directories
- Core dependencies configured (pyproject.toml)
- API client implementation (client.py)
- MCP server implementation (server.py)
- Basic test framework (test_server.py)
- Documentation files (README, SPEC, API_REFERENCE)

### 🔨 Your Tasks
1. Test the implementation with real API calls
2. Enhance error handling and edge cases
3. Improve response formatting for Claude
4. Add comprehensive tests
5. Validate the MCP integration
6. Document any issues found
7. Suggest improvements

## Environment Setup

### Prerequisites Check
```bash
cd /Users/dj/Code/brandfetch_mcp

# Verify Python version
python3 --version  # Should be 3.10+

# Check if uv is installed
which uv || echo "Install uv from: https://astral.sh/uv/install.sh"
```

### Installation Steps
```bash
# Create virtual environment
uv venv

# Activate it
source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"

# Verify installation
python -c "import mcp; import httpx; import dotenv; print('All imports successful')"
```

### API Key Setup
```bash
# Copy environment template
cp .env.example .env

# User must add their API keys manually
# Edit .env and set: BRANDFETCH_LOGO_KEY=your_logo_key_here and BRANDFETCH_BRAND_KEY=your_brand_key_here
```

**Important:** The user must provide their own Brandfetch API keys from https://brandfetch.com/developers

## Testing Strategy

### Phase 1: Unit Tests

Test the API client in isolation:

```python
# Test file: tests/test_client.py (create this)
import pytest
from brandfetch_mcp.client import BrandfetchClient

@pytest.mark.asyncio
async def test_get_brand_success():
    client = BrandfetchClient()
    result = await client.get_brand("github.com")
    
    # Assertions
    assert "name" in result
    assert "domain" in result
    assert result["domain"] == "github.com"
    assert "logos" in result
    assert "colors" in result

@pytest.mark.asyncio
async def test_search_brands():
    client = BrandfetchClient()
    results = await client.search_brands("coffee", limit=5)
    
    assert isinstance(results, list)
    assert len(results) <= 5
    if results:
        assert "name" in results[0]
        assert "domain" in results[0]

@pytest.mark.asyncio
async def test_get_brand_logo():
    client = BrandfetchClient()
    logo = await client.get_brand_logo("stripe.com", format="svg")
    
    assert "url" in logo
    assert "format" in logo
    assert logo["format"] in ["svg", "png"]
    assert logo["url"].startswith("http")

@pytest.mark.asyncio
async def test_get_brand_colors():
    client = BrandfetchClient()
    colors = await client.get_brand_colors("netflix.com")
    
    assert isinstance(colors, list)
    assert len(colors) > 0
    assert "hex" in colors[0]
    assert colors[0]["hex"].startswith("#")

@pytest.mark.asyncio
async def test_invalid_domain():
    client = BrandfetchClient()
    
    with pytest.raises(Exception):  # Should raise httpx.HTTPStatusError
        await client.get_brand("this-domain-does-not-exist-12345.com")

@pytest.mark.asyncio  
async def test_missing_api_key():
    import os
    old_logo_key = os.environ.get("BRANDFETCH_LOGO_KEY")
    old_brand_key = os.environ.get("BRANDFETCH_BRAND_KEY")
    
    try:
        if old_logo_key:
            del os.environ["BRANDFETCH_LOGO_KEY"]
        if old_brand_key:
            del os.environ["BRANDFETCH_BRAND_KEY"]
        
        with pytest.raises(ValueError, match="BRANDFETCH_BRAND_KEY"):
            BrandfetchClient()
    finally:
        if old_logo_key:
            os.environ["BRANDFETCH_LOGO_KEY"] = old_logo_key
        if old_brand_key:
            os.environ["BRANDFETCH_BRAND_KEY"] = old_brand_key
```

Run tests:
```bash
pytest tests/ -v
pytest tests/test_client.py -v -s  # With output
```

### Phase 2: Manual API Testing

Test the client directly:

```python
# Create: manual_test.py
import asyncio
from brandfetch_mcp.client import BrandfetchClient

async def main():
    client = BrandfetchClient()
    
    print("\n=== Testing get_brand ===")
    try:
        brand = await client.get_brand("github.com")
        print(f"Brand: {brand['name']}")
        print(f"Logos: {len(brand.get('logos', []))}")
        print(f"Colors: {len(brand.get('colors', []))}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing search_brands ===")
    try:
        results = await client.search_brands("coffee", limit=3)
        print(f"Found {len(results)} results")
        for r in results[:3]:
            print(f"  - {r.get('name')}: {r.get('domain')}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing get_brand_logo ===")
    try:
        logo = await client.get_brand_logo("stripe.com", format="svg")
        print(f"Logo URL: {logo['url'][:60]}...")
        print(f"Format: {logo['format']}, Theme: {logo['theme']}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== Testing get_brand_colors ===")
    try:
        colors = await client.get_brand_colors("netflix.com")
        print(f"Found {len(colors)} colors")
        for c in colors[:3]:
            print(f"  {c.get('hex')} ({c.get('type')})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it:
```bash
python manual_test.py
```

### Phase 3: MCP Server Testing

Test with MCP Inspector:

```bash
# Install MCP Inspector (requires Node.js)
npm install -g @modelcontextprotocol/inspector

# Test the server
npx @modelcontextprotocol/inspector uv --directory /Users/dj/Code/brandfetch_mcp run mcp-brandfetch
```

In the Inspector:
1. Verify all 4 tools are listed
2. Test each tool with sample inputs
3. Check error handling with invalid inputs
4. Verify response formats

### Phase 4: Claude Desktop Integration

Configure Claude Desktop (~/Library/Application Support/Claude/claude_desktop_config.json):

```json
{
  "mcpServers": {
    "brandfetch": {
      "command": "uv",
      "args": [
        "--directory",
        "/Users/dj/Code/brandfetch_mcp",
        "run",
        "mcp-brandfetch"
      ],
      "env": {
        "BRANDFETCH_LOGO_KEY": "your_logo_key_here",
        "BRANDFETCH_BRAND_KEY": "your_brand_key_here"
      }
    }
  }
}
```

Test queries in Claude:
- "Get brand details for github.com"
- "Search for brands related to coffee"
- "What are the brand colors for stripe.com?"
- "Find the SVG logo for netflix.com"

Check for:
- Tool execution success
- Response readability
- Error message clarity
- Performance/speed

## Code Improvements to Consider

### 1. Enhanced Error Handling

**Current:** Basic exception catching  
**Improve:** Specific error messages and recovery

```python
# In client.py, enhance error handling:

async def get_brand(self, domain: str) -> Dict[str, Any]:
    """Retrieve comprehensive brand data."""
    # Strip protocol and www if present
    domain = domain.replace("https://", "").replace("http://", "")
    domain = domain.replace("www.", "").strip("/")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/brands/{domain}",
                headers=self.headers,
                timeout=30.0,
            )
            response.raise_for_status()
            return response.json()
    
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"Brand not found for domain: {domain}")
        elif e.response.status_code == 401:
            raise ValueError("Invalid API key. Check BRANDFETCH_BRAND_KEY.")
        elif e.response.status_code == 429:
            raise ValueError("Rate limit exceeded. Try again later.")
        else:
            raise ValueError(f"API error {e.response.status_code}: {e.response.text}")
    
    except httpx.TimeoutException:
        raise ValueError(f"Request timeout for domain: {domain}")
    
    except Exception as e:
        raise ValueError(f"Unexpected error: {str(e)}")
```

### 2. Better Response Formatting

**Current:** Returns raw Python dict as string  
**Improve:** Format for readability in Claude

```python
# In server.py, improve response formatting:

import json

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    try:
        if name == "get_brand_details":
            domain = arguments["domain"]
            result = await brandfetch.get_brand(domain)
            
            # Format nicely for Claude
            formatted = format_brand_details(result)
            return [TextContent(type="text", text=formatted)]
        
        # ... similar for other tools

def format_brand_details(data: Dict[str, Any]) -> str:
    """Format brand data for readability."""
    output = []
    output.append(f"# {data.get('name', 'Unknown')} ({data.get('domain')})")
    output.append(f"\n**Description:** {data.get('description', 'N/A')}")
    
    # Logos
    logos = data.get('logos', [])
    if logos:
        output.append(f"\n**Logos:** {len(logos)} available")
        for logo in logos[:3]:
            formats = logo.get('formats', [])
            if formats:
                output.append(f"  - {logo.get('type', 'logo')} ({logo.get('theme', 'light')}): {formats[0].get('src', '')}")
    
    # Colors
    colors = data.get('colors', [])
    if colors:
        output.append(f"\n**Colors:**")
        for color in colors:
            output.append(f"  - {color.get('hex')} ({color.get('type', 'unknown')})")
    
    # Fonts
    fonts = data.get('fonts', [])
    if fonts:
        output.append(f"\n**Fonts:**")
        for font in fonts:
            output.append(f"  - {font.get('name')} ({font.get('type', 'unknown')})")
    
    # Social Links
    links = data.get('links', [])
    if links:
        output.append(f"\n**Social Links:**")
        for link in links[:5]:
            output.append(f"  - {link.get('name')}: {link.get('url')}")
    
    return "\n".join(output)
```

### 3. Input Validation

Add validation for common mistakes:

```python
def validate_domain(domain: str) -> str:
    """Validate and normalize domain."""
    if not domain or not isinstance(domain, str):
        raise ValueError("Domain must be a non-empty string")
    
    # Remove protocol
    domain = domain.replace("https://", "").replace("http://", "")
    
    # Remove www
    domain = domain.replace("www.", "")
    
    # Remove trailing slashes and whitespace
    domain = domain.strip().strip("/")
    
    # Convert to lowercase
    domain = domain.lower()
    
    # Basic validation
    if "." not in domain:
        raise ValueError(f"Invalid domain format: {domain}")
    
    return domain
```

### 4. Response Caching (Optional)

For repeated queries:

```python
from functools import lru_cache
import time

class BrandfetchClient:
    def __init__(self, api_key: Optional[str] = None):
        # ... existing code ...
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def get_brand(self, domain: str) -> Dict[str, Any]:
        cache_key = f"brand:{domain}"
        
        # Check cache
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.info(f"Cache hit for {domain}")
                return cached_data
        
        # Fetch from API
        result = await self._fetch_brand(domain)
        
        # Store in cache
        self._cache[cache_key] = (result, time.time())
        
        return result
```

### 5. Logging Improvements

Add structured logging:

```python
import logging
import json

# Configure logging with more detail
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger("brandfetch-mcp")

# Log with context
logger.info("API call", extra={
    "tool": "get_brand",
    "domain": domain,
    "timestamp": time.time()
})
```

## Common Issues and Solutions

### Issue 1: Import Errors
**Symptom:** `ModuleNotFoundError: No module named 'mcp'`

**Solution:**
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall dependencies
uv pip install -e ".[dev]"

# Verify
python -c "import mcp; print(mcp.__file__)"
```

### Issue 2: API Key Not Found
**Symptom:** `ValueError: BRANDFETCH_BRAND_KEY must be set`

**Solution:**
```bash
# Check .env file exists
cat .env

# Verify key is loaded
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(os.getenv('BRANDFETCH_BRAND_KEY'))"

# Ensure .env is in project root
ls -la /Users/dj/Code/brandfetch_mcp/.env
```

### Issue 3: Claude Desktop Not Showing Tools
**Symptom:** No hammer icon in Claude Desktop

**Solution:**
1. Check config syntax (must be valid JSON)
2. Verify absolute paths (no ~, use full /Users/dj/...)
3. Check Claude Desktop logs: Settings → Developer
4. Restart Claude Desktop completely
5. Test server manually: `uv run mcp-brandfetch`

### Issue 4: Rate Limiting
**Symptom:** `429 Too Many Requests`

**Solution:**
- Implement caching (see above)
- Add delays between requests
- Upgrade Brandfetch API plan
- Show clear error message to user

### Issue 5: Malformed API Responses
**Symptom:** Missing fields in response

**Solution:**
```python
# Add defensive checks
logos = data.get('logos', [])
if logos and isinstance(logos, list):
    # Process logos
else:
    logger.warning(f"No logos found for {domain}")
```

## Testing Checklist

Before considering the implementation complete:

### Functionality
- [ ] get_brand_details works for valid domains
- [ ] search_brands returns results
- [ ] get_brand_logo retrieves logos correctly
- [ ] get_brand_colors extracts color palette
- [ ] All tools handle errors gracefully

### Error Handling
- [ ] Invalid domain returns clear error
- [ ] Missing API keys show helpful message
- [ ] Rate limiting is communicated clearly
- [ ] Network errors are caught
- [ ] Malformed responses handled

### Integration
- [ ] MCP Inspector shows all 4 tools
- [ ] Tools work in MCP Inspector
- [ ] Claude Desktop loads server
- [ ] Tools execute in Claude Desktop
- [ ] Responses are readable in Claude

### Code Quality
- [ ] All tests pass: `pytest -v`
- [ ] No linting errors: `ruff check src/`
- [ ] Code is formatted: `black src/ tests/`
- [ ] Type hints are present
- [ ] Docstrings are complete

### Documentation
- [ ] README is accurate
- [ ] Example queries work
- [ ] API_REFERENCE matches actual API
- [ ] Installation steps are correct

## Performance Considerations

### API Rate Limits
- Free tier: ~100 requests/month
- Be conservative during testing
- Use caching for repeated queries

### Response Times
- Typical API response: 500ms - 2s
- Set appropriate timeouts (30s default)
- Consider streaming for large datasets

### Memory Usage
- Brand data can be large (multiple MB)
- Don't cache excessively
- Clean up old cache entries

## Security Considerations

### API Key Protection
- Never commit .env file
- Never log API key
- Use environment variables only
- Rotate keys if exposed

### Input Sanitization
- Validate domain format
- Prevent injection attacks
- Limit response sizes
- Sanitize error messages

## Completion Criteria

The implementation is considered complete when:

1. **All 4 tools work correctly** with real API
2. **Tests pass** (minimum 80% coverage)
3. **Works in Claude Desktop** without errors
4. **Error messages are clear** and actionable
5. **Code is clean** (formatted, linted, typed)
6. **Documentation is accurate** and tested
7. **Edge cases handled** (invalid input, API errors)
8. **Performance is acceptable** (<5s per request)

## Reporting Results

After testing, create a report:

```markdown
# Brandfetch MCP Server Test Report

## Test Environment
- Python version: X.X.X
- MCP SDK version: X.X.X
- Brandfetch API: Working / Not Working
- Date: YYYY-MM-DD

## Test Results

### Unit Tests
- Total: X tests
- Passed: X
- Failed: X
- Coverage: XX%

### Integration Tests
- MCP Inspector: ✅/❌
- Claude Desktop: ✅/❌

### Performance
- Average response time: Xms
- Max response time: Xms

### Issues Found
1. [Issue description]
2. [Issue description]

### Improvements Made
1. [Improvement description]
2. [Improvement description]

### Recommendations
- [Recommendation 1]
- [Recommendation 2]
```

## Additional Features (Optional)

If time permits, consider adding:

### 1. Additional Tools
```python
Tool(
    name="get_brand_fonts",
    description="Get brand typography/font information",
    inputSchema={...}
)

Tool(
    name="get_brand_images",
    description="Retrieve brand images and banners",
    inputSchema={...}
)

Tool(
    name="get_brand_social_links",
    description="Extract social media profiles",
    inputSchema={...}
)
```

### 2. Batch Operations
```python
Tool(
    name="compare_brands",
    description="Compare multiple brands side by side",
    inputSchema={
        "domains": {"type": "array", "items": {"type": "string"}}
    }
)
```

### 3. Export Functionality
```python
Tool(
    name="export_brand_kit",
    description="Export complete brand kit as JSON/markdown",
    inputSchema={...}
)
```

## Resources

### Documentation
- [MCP Specification](https://spec.modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Brandfetch API Docs](https://docs.brandfetch.com)
- [MCP Python SDK Examples](https://github.com/modelcontextprotocol/python-sdk/tree/main/examples)

### Tools
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
- [pytest Documentation](https://docs.pytest.org)
- [httpx Documentation](https://www.python-httpx.org)

### Similar Projects
Browse other MCP servers for inspiration:
- https://github.com/modelcontextprotocol/servers

## Questions to Ask the User

If you encounter ambiguity:

1. **Formatting:** "Should responses be formatted as markdown or JSON?"
2. **Caching:** "Do you want response caching implemented?"
3. **Additional Tools:** "Should I add tools for fonts, images, or social links?"
4. **Error Verbosity:** "How detailed should error messages be?"
5. **Performance:** "Is response time under 5 seconds acceptable?"
6. **Testing:** "Do you want integration tests for Claude Desktop?"

## Final Notes

### Key Principles
- **Reliability over features** - Focus on making the 4 core tools bulletproof
- **Clear errors** - Since this is for AI model testing, error clarity is critical
- **Simplicity** - Don't over-engineer unless requested
- **User experience** - Responses should be readable in Claude Desktop

### Development Philosophy
This is a tool for:
- Testing AI model capabilities
- Developing evaluation prompts
- Demonstrating MCP integration

Therefore prioritize:
- Deterministic behavior
- Comprehensive error messages
- Well-documented code
- Reproducible results

### Success Looks Like
- User can ask Claude "Get brand details for X.com"
- Claude uses the tool successfully
- Response is clear and accurate
- Errors (if any) are actionable
- The experience is smooth and reliable

Good luck! This is a straightforward project with a clear scope. Focus on testing thoroughly and making the error messages excellent.
