"""MCP server implementation for Brandfetch API."""

import asyncio
import logging
from typing import Any, Dict
import httpx
from mcp.server import Server
from mcp.types import Tool, TextContent
from pydantic import AnyUrl

from .brand_logo import get_logo_url
from .client import BrandfetchClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("brandfetch-mcp")

# Initialize MCP server
app = Server("brandfetch-mcp")

# Initialize Brandfetch client
try:
    brandfetch = BrandfetchClient()
    logger.info("Brandfetch client initialized successfully")
except ValueError as e:
    logger.error(f"Failed to initialize Brandfetch client: {e}")
    raise


def format_brand_details(data: Dict[str, Any]) -> str:
    """Format brand data for readability in Claude."""
    lines = []
    
    # Header
    name = data.get('name', 'Unknown Brand')
    domain = data.get('domain', 'N/A')
    lines.append(f"# {name} ({domain})")
    
    # Description
    if desc := data.get('description'):
        lines.append(f"\n**Description:** {desc}")
    
    # Company info
    if company := data.get('company'):
        lines.append(f"\n**Company Details:**")
        if employees := company.get('employees'):
            lines.append(f"  - Employees: {employees:,}")
        if founded := company.get('foundedYear'):
            lines.append(f"  - Founded: {founded}")
        if location := company.get('location'):
            city = location.get('city', 'N/A')
            country = location.get('country', 'N/A')
            lines.append(f"  - Location: {city}, {country}")
    
    # Logos
    logos = data.get('logos', [])
    if logos:
        lines.append(f"\n**Available Logos:** {len(logos)}")
        for logo in logos[:3]:  # Show first 3
            logo_type = logo.get('type', 'logo')
            theme = logo.get('theme', 'light')
            formats = logo.get('formats', [])
            if formats:
                format_info = formats[0]
                url = format_info.get('src', 'N/A')
                format_type = format_info.get('format', 'unknown')
                size = format_info.get('size', 0)
                lines.append(f"  - {logo_type} ({theme}, {format_type}): {url[:80]}{'...' if len(url) > 80 else ''} ({size:,} bytes)")
        
        if len(logos) > 3:
            lines.append(f"  - ... and {len(logos) - 3} more")
    
    # Colors
    colors = data.get('colors', [])
    if colors:
        lines.append(f"\n**Brand Colors:**")
        for color in colors[:5]:  # Show first 5
            hex_code = color.get('hex', '#000000')
            color_type = color.get('type', 'unknown')
            brightness = color.get('brightness', 'N/A')
            lines.append(f"  - {hex_code} ({color_type}, brightness: {brightness})")
        
        if len(colors) > 5:
            lines.append(f"  - ... and {len(colors) - 5} more")
    
    # Fonts
    fonts = data.get('fonts', [])
    if fonts:
        lines.append(f"\n**Typography:**")
        for font in fonts:
            name = font.get('name', 'Unknown')
            font_type = font.get('type', 'body')
            origin = font.get('origin', 'unknown')
            lines.append(f"  - {name} ({font_type}, {origin})")
    
    # Social Links
    links = data.get('links', [])
    if links:
        lines.append(f"\n**Social Media:**")
        for link in links[:5]:  # Show first 5
            platform = link.get('name', 'unknown')
            url = link.get('url', '')
            lines.append(f"  - {platform}: {url}")
        
        if len(links) > 5:
            lines.append(f"  - ... and {len(links) - 5} more")
    
    # Additional info
    if claimed := data.get('claimed'):
        lines.append(f"\n**Brand Status:** ✓ Claimed")
    else:
        lines.append(f"\n**Brand Status:** Unclaimed")
    
    if quality := data.get('qualityScore'):
        lines.append(f"**Quality Score:** {quality:.2%}")
    
    return "\n".join(lines)


def format_search_results(results: list) -> str:
    """Format search results for readability."""
    if not results:
        return "No brands found matching your search. Try different keywords."
    
    lines = [f"Found {len(results)} brands:\n"]
    
    for i, brand in enumerate(results, 1):
        name = brand.get('name', 'Unknown')
        domain = brand.get('domain', 'N/A')
        claimed = "✓ Claimed" if brand.get('claimed') else "Unclaimed"
        desc = brand.get('description', '')
        
        lines.append(f"{i}. **{name}** ({domain}) - {claimed}")
        if desc:
            # Truncate long descriptions
            short_desc = desc[:100] + "..." if len(desc) > 100 else desc
            lines.append(f"   {short_desc}")
        lines.append("")  # Empty line for readability
    
    return "\n".join(lines)


def format_logo_response(logo: dict) -> str:
    """Format logo response for readability."""
    lines = [
        f"**Logo URL:** {logo.get('url', 'N/A')}",
        f"**Format:** {logo.get('format', 'N/A')}",
        f"**Theme:** {logo.get('theme', 'N/A')}",
        f"**Type:** {logo.get('type', 'N/A')}"
    ]
    
    # Add metadata if available
    if metadata := logo.get('metadata'):
        lines.append(f"\n**Details:**")
        if size := metadata.get('size'):
            lines.append(f"  - Size: {size:,} bytes")
        if width := metadata.get('width'):
            height = metadata.get('height', 0)
            lines.append(f"  - Dimensions: {width}x{height}px")
        if bg := metadata.get('background'):
            lines.append(f"  - Background: {bg}")
    
    # Add note if present
    if note := logo.get('note'):
        lines.append(f"\n*Note: {note}*")
    
    return "\n".join(lines)


def format_colors_response(colors: list) -> str:
    """Format color palette for readability."""
    if not colors:
        return "No colors found for this brand."
    
    lines = [f"**Brand Color Palette:** {len(colors)} colors\n"]
    
    # Group by type for better organization
    by_type = {}
    for color in colors:
        color_type = color.get('type', 'unknown')
        if color_type not in by_type:
            by_type[color_type] = []
        by_type[color_type].append(color)
    
    # Display in organized groups
    type_order = ['brand', 'accent', 'primary', 'secondary', 'dark', 'light', 'unknown']
    
    for color_type in type_order:
        if color_type in by_type:
            lines.append(f"**{color_type.title()} Colors:**")
            for color in by_type[color_type]:
                hex_code = color.get('hex', '#000000')
                brightness = color.get('brightness', 'N/A')
                lines.append(f"  • {hex_code} (brightness: {brightness})")
            lines.append("")
    
    return "\n".join(lines).strip()


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available MCP tools."""
    return [
        Tool(
            name="get_brand_details",
            description="Retrieve comprehensive brand information including logos, colors, fonts, and social links for a given domain",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The company domain (e.g., 'github.com')",
                    }
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="search_brands",
            description="Search for brands by name or keyword. Returns a list of matching brands with basic information.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search term or brand name",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="get_brand_logo",
            description="Retrieve brand logo in specified format. Returns logo URL and metadata.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The company domain (e.g., 'stripe.com')",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["svg", "png"],
                        "description": "Desired logo format",
                        "default": "svg",
                    },
                    "theme": {
                        "type": "string",
                        "enum": ["light", "dark"],
                        "description": "Logo theme/color scheme",
                        "default": "light",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["logo", "icon", "symbol"],
                        "description": "Type of logo asset",
                        "default": "logo",
                    },
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="get_brand_colors",
            description="Extract the brand color palette with hex codes and color types (primary, secondary, accent, etc.)",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The company domain (e.g., 'netflix.com')",
                    }
                },
                "required": ["domain"],
            },
        ),
        Tool(
            name="get_logo_url",
            description="Get a brand logo URL quickly using domain lookup or name search with heuristics. Returns the logo URL and source method used.",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "The company domain (e.g., 'github.com') - preferred for fastest lookup",
                    },
                    "name": {
                        "type": "string",
                        "description": "Brand name to search (e.g., 'GitHub') - uses heuristics then API fallback",
                    }
                },
                "oneOf": [
                    {"required": ["domain"]},
                    {"required": ["name"]}
                ],
            },
        ),

    ]
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent]:
    """Handle tool execution requests."""
    try:
        if name == "get_brand_details":
            domain = arguments["domain"]
            logger.info(f"Fetching brand details for: {domain}")
            result = await brandfetch.get_brand(domain)
            formatted = format_brand_details(result)
            return [TextContent(type="text", text=formatted)]

        elif name == "search_brands":
            query = arguments["query"]
            limit = arguments.get("limit", 10)
            logger.info(f"Searching brands for: {query} (limit: {limit})")
            result = await brandfetch.search_brands(query, limit)
            formatted = format_search_results(result)
            return [TextContent(type="text", text=formatted)]

        elif name == "get_brand_logo":
            domain = arguments["domain"]
            format = arguments.get("format", "svg")
            theme = arguments.get("theme", "light")
            logo_type = arguments.get("type", "logo")
            logger.info(f"Fetching {format} logo for: {domain} (theme: {theme}, type: {logo_type})")
            result = await brandfetch.get_brand_logo(domain, format, theme, logo_type)
            formatted = format_logo_response(result)
            return [TextContent(type="text", text=formatted)]

        elif name == "get_brand_colors":
            domain = arguments["domain"]
            logger.info(f"Fetching brand colors for: {domain}")
            result = await brandfetch.get_brand_colors(domain)
            formatted = format_colors_response(result)
            return [TextContent(type="text", text=formatted)]

        elif name == "get_logo_url":
            domain = arguments.get("domain")
            name_param = arguments.get("name")
            logger.info(f"Getting logo URL for domain='{domain}' or name='{name_param}'")
            
            # Use the new high-quota logo lookup strategy
            try:
                from .brandfetch_logo_lookup_checked import get_logo_for_domain
                
                # If domain is provided, use it directly; otherwise use name as company hint
                if domain:
                    result = await get_logo_for_domain(domain)
                elif name_param:
                    # Try to generate domain from name or use as company hint
                    result = await get_logo_for_domain(name_param, company_hint=name_param)
                else:
                    raise ValueError("Either domain or name must be provided")
                
                if "logo_url" in result:
                    response = f"**Logo URL:** {result['logo_url']}\n**Source:** {result['source']}\n**Reason:** {result['reason']}"
                    if result.get("warning"):
                        response += f"\n**Warning:** {result['warning']}"
                    response += f"\n**Brand API calls this month:** {result.get('brand_api_calls_this_month', 0)}"
                elif "error" in result:
                    if result["error"] == "brand_api_limit_reached":
                        response = f"❌ **Brand API limit reached** ({result.get('brand_api_calls_this_month', 0)} calls). Try again next month."
                    elif result["error"] == "no_logo_found":
                        response = f"❌ **No logo found** for the specified domain/name."
                    else:
                        response = f"❌ **Error:** {result.get('message', 'Unknown error')}"
                else:
                    response = "❌ **Unexpected error:** No valid response received."
                    
            except Exception as e:
                logger.error(f"Error in get_logo_url: {e}")
                response = f"❌ **Error:** {str(e)}"
            
            return [TextContent(type="text", text=response)]

        else:
            raise ValueError(f"Unknown tool: {name}")

    except ValueError as e:
        # Handle our custom error messages
        error_msg = str(e)
        logger.error(f"ValueError in {name}: {error_msg}")
        return [TextContent(type="text", text=f"❌ Error: {error_msg}")]

    except httpx.HTTPStatusError as e:
        # Handle HTTP errors with context
        status = e.response.status_code
        error_msg = f"API error ({status}): {e.response.text}"
        logger.error(f"HTTPStatusError in {name}: {error_msg}")
        return [TextContent(type="text", text=f"❌ API Error: {error_msg}")]

    except Exception as e:
        # Handle unexpected errors
        error_msg = f"Unexpected error executing {name}: {str(e)}"
        logger.error(error_msg)
        return [TextContent(type="text", text=f"❌ Error: {error_msg}")]


async def main():
    """Main entry point for the MCP server."""
    from mcp.server.stdio import stdio_server

    logger.info("Starting Brandfetch MCP server...")

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )


def run():
    """Synchronous entry point for command-line execution."""
    asyncio.run(main())


if __name__ == "__main__":
    run()
