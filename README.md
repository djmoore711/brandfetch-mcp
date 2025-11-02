# Brandfetch MCP Server

[![Project Status](https://img.shields.io/badge/status-active-success.svg)]()

Model Context Protocol (MCP) server that lets AI assistants fetch logos, colors, fonts, and company info from the Brandfetch API.

## Features

- **get_brand_details** – Full brand profile by domain
- **search_brands** – Keyword search for matching brands
- **get_brand_logo** – SVG/PNG assets in light/dark themes
- **get_brand_colors** – Curated color palettes with metadata
- **get_logo_url** – Fast logo URL lookup by domain
- **Persistent usage tracking** – SQLite-based quota management

## Smart API Usage

This server prioritizes the **Logo-by-Domain API** (high quota, unlimited usage) and only falls back to the **Brand API** (limited quota) when necessary:

1. **Domain lookup first** - Direct logo-by-domain API calls with high usage limits
2. **Brand API fallback** - Only used when domain lookup fails, with monthly quota tracking
3. **Persistent usage tracking** - SQLite-based counter prevents quota overages
4. **Warning system** - Alerts when approaching Brand API limits

## Requirements

- Python 3.10+
- Brandfetch API keys (both Logo and Brand API)
- [uv](https://astral.sh/uv) (recommended package manager)

## API Key Setup

You need two API keys from Brandfetch:
1. **Logo API Key** (high quota, for domain lookups)
2. **Brand API Key** (limited quota, for fallback searches)

Add both to your `.env` file:
```env
BRANDFETCH_LOGO_KEY="your_logo_api_key_here"
BRANDFETCH_BRAND_KEY="your_brand_api_key_here"
```

## Quickstart (one page)

1. **Get the right API keys**  
   Visit <https://brandfetch.com/developers> and get **both** keys:
   - **Logo API Key** - For high-quota domain lookups
   - **Brand API Key** - For fallback searches (limited quota)  
   → Need screenshots? See [API_KEY_SETUP.md](API_KEY_SETUP.md).

2. **Run locally with Python**
   ```bash
   uv venv && source .venv/bin/activate
   uv pip install -e ".[dev]"
   cp .env.example .env  # then add both BRANDFETCH_LOGO_KEY and BRANDFETCH_BRAND_KEY
   python manual_test.py
   ```

3. **Run with Docker (optional)**
   ```bash
   docker build -t brandfetch-mcp .
   docker run --rm \
     -e BRANDFETCH_LOGO_KEY=your_logo_key \
     -e BRANDFETCH_BRAND_KEY=your_brand_key \
     brandfetch-mcp
   ```

4. **Wire up Claude Desktop**
   ```json
   {
     "mcpServers": {
       "brandfetch": {
         "command": "uv",
         "args": ["--directory", "/absolute/path/to/brandfetch_mcp", "run", "mcp-brandfetch"],
         "env": { 
           "BRANDFETCH_LOGO_KEY": "your_logo_key",
           "BRANDFETCH_BRAND_KEY": "your_brand_key"
         }
       }
     }
   }
   ```
   Restart Claude Desktop; look for the hammer icon.

## Project Structure
Key files:
- `src/brandfetch_mcp/server.py`: Main MCP server implementation
- `src/brandfetch_mcp/client.py`: Brandfetch API client
- `src/brandfetch_mcp/brandfetch_logo_lookup_checked.py`: Logo lookup functionality

## Usage

### Quick health check
```bash
curl -H "Authorization: Bearer YOUR_KEY" https://api.brandfetch.io/v2/brands/github.com
```

### Handy prompts
- "Get brand details for stripe.com"
- "Search for coffee brands"
- "Fetch the SVG logo for github.com"
- "What color palette does netflix.com use?"
- "Get a logo URL for github.com" (fast domain lookup)
- "Find the logo for GitHub" (name search with heuristics)

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/fooBar`)
3. Commit your changes (`git commit -am 'Add some fooBar'`)
4. Push to the branch (`git push origin feature/fooBar`)
5. Create a new Pull Request

## License

[MIT](LICENSE)

## Troubleshooting

| Issue | Fix |
| --- | --- |
| 401 Unauthorized | You grabbed the Logo API key—generate the **Brand API** key instead. |
| No hammer icon in Claude | Check Claude Desktop → Settings → Developer logs; verify JSON and absolute paths. |
| Import errors | Activate the venv and rerun `uv pip install -e ".[dev]"`. |

## Known Limitations

- **Development Mode**: Must run from project root directory (`.env` path resolution works in development mode only)
- **Test Coverage**: Some get_brand_logo tests mock wrong layer - functionality works but tests need updating
- **Pip Installation**: Environment file loading only works when running from source, not pip-installed packages

## Support

- Open GitHub issues for bugs/requests
- [Brandfetch API docs](https://docs.brandfetch.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
- More setup detail: [API_KEY_SETUP.md](API_KEY_SETUP.md)
