import os
import httpx
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BrandfetchClient:
    def __init__(self):
        self.base_url = "https://api.brandfetch.io/v2"
        # Use Brand API key for /brands and /search endpoints
        self.api_key = os.getenv("BRANDFETCH_API_KEY")
        self.client_id = os.getenv("BRANDFETCH_CLIENT_ID")
        
        if not self.api_key or not self.api_key.strip():
            raise ValueError("BRANDFETCH_API_KEY must be set in .env")
        

        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "Brandfetch-MCP/0.2.0",
        }
        # Create a transport with retries
        transport = httpx.AsyncHTTPTransport(retries=3)
        self.client = httpx.AsyncClient(transport=transport, headers=self.headers, timeout=30.0)

    async def close(self):
        """Close the underlying HTTP client."""
        await self.client.aclose()

    def _append_client_id(self, url: str) -> str:
        """
        Append client ID to CDN URLs for Brandfetch hotlinking compliance.
        Only applies to cdn.brandfetch.io URLs.
        """
        if not self.client_id:
            return url
        
        parsed = urlparse(url)
        if "cdn.brandfetch.io" not in parsed.netloc:
            return url
        
        # Parse existing query parameters
        query_params = parse_qs(parsed.query)
        query_params['c'] = [self.client_id]
        
        # Rebuild URL with client ID
        new_parsed = parsed._replace(query=urlencode(query_params, doseq=True))
        return urlunparse(new_parsed)

    def _clean_domain(self, domain: str) -> str:
        """Clean and normalize domain input."""
        # Strip whitespace from input first
        domain = domain.strip()
        
        if not domain:
            raise ValueError("Domain cannot be empty")
        
        # Parse URL to extract domain properly
        parsed = urlparse(domain)
        clean_domain = parsed.netloc or parsed.path  # netloc for URLs, path for plain domains
        
        # Remove www prefix (case-insensitive) and convert to lowercase
        if clean_domain.lower().startswith("www."):
            clean_domain = clean_domain[4:]  # Remove "www."
        clean_domain = clean_domain.lower()
        
        # Validate domain format
        clean_domain = clean_domain.strip("/")
        if not clean_domain or "." not in clean_domain:
            raise ValueError(f"Invalid domain format: {domain}")
        
        return clean_domain

    async def get_brand(self, domain: str) -> Dict[str, Any]:
        """Retrieve comprehensive brand data for a domain."""
        # Clean domain input
        domain = self._clean_domain(domain)
        
        try:
            response = await self.client.get(
                f"{self.base_url}/brands/{domain}",
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(f"Brand not found for domain: {domain}") from e
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key. Check BRANDFETCH_API_KEY.") from e
            elif e.response.status_code == 429:
                raise ValueError("Rate limit exceeded. Try again later.") from e
            else:
                raise ValueError(f"API error {e.response.status_code}: {e.response.text}") from e
        except httpx.TimeoutException:
            raise ValueError(f"Request timeout for domain: {domain}") from None
        except Exception as e:
            raise ValueError(f"Unexpected error: {str(e)}") from e

    async def search_brands(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for brands by name or keyword.
        
        Note: The search endpoint requires a Brandfetch Pro subscription.
        Free tier accounts only have access to individual brand lookups.
        """
        try:
            response = await self.client.get(
                f"{self.base_url}/search",
                params={"q": query, "limit": min(limit, 50)},
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                raise ValueError("Invalid search query") from e
            elif e.response.status_code == 401:
                raise ValueError("Invalid API key. Check BRANDFETCH_API_KEY.") from e
            elif e.response.status_code == 403:
                raise ValueError(
                    "Search endpoint requires Brandfetch Pro subscription. "
                    "Free tier accounts only support individual brand lookups. "
                    "Upgrade at https://brandfetch.com/pricing"
                ) from e
            elif e.response.status_code == 429:
                raise ValueError("Rate limit exceeded. Try again later.") from e
            else:
                raise ValueError(f"API error {e.response.status_code}: {e.response.text}") from e
        except httpx.TimeoutException:
            raise ValueError("Search request timed out") from None
        except Exception as e:
            raise ValueError(f"Unexpected error: {str(e)}") from e

    async def get_brand_logo(self, domain: str, format: str = "svg", theme: str = "light", type: str = "logo") -> Dict[str, Any]:
        """Retrieve brand logo in specified format."""
        # Clean domain input
        domain = self._clean_domain(domain)
        
        # Get brand data first
        try:
            brand_data = await self.get_brand(domain)
        except ValueError as e:
            raise e  # Re-raise the error from get_brand
        
        # Find the best matching logo
        logos = brand_data.get("logos", [])
        best_logo = None
        
        # Filter by preferences
        filtered_logos = []
        for logo in logos:
            if logo.get("theme") == theme and logo.get("type") == type:
                filtered_logos.append(logo)
        
        # If no exact match, use any logo with preferred format
        if not filtered_logos:
            for logo in logos:
                if logo.get("type") == type:
                    filtered_logos.append(logo)
        
        # Still no match, use any logo
        if not filtered_logos:
            filtered_logos = logos
        
        if filtered_logos:
            best_logo = filtered_logos[0]
            
            # Find the specific format
            formats = best_logo.get("formats", [])
            target_format = None
            
            for fmt in formats:
                if fmt.get("format") == format:
                    target_format = fmt
                    break
            
            # If preferred format not found, use first available
            if not target_format and formats:
                target_format = formats[0]
            
            if target_format:
                return {
                    "url": self._append_client_id(target_format.get("src")),
                    "format": target_format.get("format"),
                    "theme": best_logo.get("theme"),
                    "type": best_logo.get("type"),
                    "metadata": {
                        "size": target_format.get("size"),
                        "width": target_format.get("width"),
                        "height": target_format.get("height"),
                        "background": best_logo.get("background")
                    }
                }
        
        raise ValueError(f"No logo found for {domain} with specified criteria")

    async def get_brand_colors(self, domain: str) -> List[Dict[str, Any]]:
        """Extract brand color palette."""
        # Clean domain input
        domain = self._clean_domain(domain)
        
        # Get brand data first
        try:
            brand_data = await self.get_brand(domain)
        except ValueError as e:
            raise e  # Re-raise the error from get_brand
        
        # Return colors with additional metadata
        colors = brand_data.get("colors", [])
        
        # Enhance color data
        enhanced_colors = []
        for color in colors:
            enhanced_color = {
                "hex": color.get("hex"),
                "type": color.get("type", "unknown"),
                "brightness": color.get("brightness", "unknown")
            }
            enhanced_colors.append(enhanced_color)
        
        return enhanced_colors