# Brandfetch MCP Server

Model Context Protocol (MCP) server that lets AI assistants fetch logos, colors, fonts, and company info from the Brandfetch Brand API.

## Features

- **get_brand_details** – full brand profile by domain
- **search_brands** – keyword search for matching brands
- **get_brand_logo** – SVG/PNG assets in light/dark themes
- **get_brand_colors** – curated color palettes with metadata

## Quickstart (one page)

1. **Get the right API key**  
   Visit <https://brandfetch.com/developers>, choose **Brand API** (not Logo API), and copy the key.  
   → Need screenshots? See [API_KEY_SETUP.md](API_KEY_SETUP.md).

2. **Run locally with Python**
   ```bash
   uv venv && source .venv/bin/activate
   uv pip install -e ".[dev]"
   cp .env.example .env  # then add BRANDFETCH_API_KEY
   python manual_test.py
   ```

3. **Run with Docker (optional)**
   ```bash
   docker build -t brandfetch-mcp .
   docker run --rm \
     -e BRANDFETCH_API_KEY=your_actual_key \
     brandfetch-mcp
   ```

4. **Wire up Claude Desktop**
   ```json
   {
     "mcpServers": {
       "brandfetch": {
         "command": "uv",
         "args": ["--directory", "/absolute/path/to/brandfetch_mcp", "run", "mcp-brandfetch"],
         "env": { "BRANDFETCH_API_KEY": "your_actual_key" }
       }
     }
   }
   ```
   Restart Claude Desktop; look for the hammer icon.

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

## Troubleshooting

| Issue | Fix |
| --- | --- |
| 401 Unauthorized | You grabbed the Logo API key—generate the **Brand API** key instead. |
| No hammer icon in Claude | Check Claude Desktop → Settings → Developer logs; verify JSON and absolute paths. |
| Import errors | Activate the venv and rerun `uv pip install -e ".[dev]"`. |

## Feedback & Resources

- Open GitHub issues for bugs/requests
- [Brandfetch API docs](https://docs.brandfetch.com)
- [Model Context Protocol](https://modelcontextprotocol.io)
- More setup detail: [API_KEY_SETUP.md](API_KEY_SETUP.md)
