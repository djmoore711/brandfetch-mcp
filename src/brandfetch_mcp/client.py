"""Brandfetch API client for making HTTP requests."""

import os
from dotenv import load_dotenv
import time
from typing import Any, Dict, List, Optional
import httpx
import logging

# Load environment variables from .env file
from pathlib import Path
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(env_path, override=False)  # Use relative path, don't override existing env vars

# Configure logging
logger = logging.getLogger("brandfetch-mcp")


class BrandfetchClient:
    """Client for interacting with the Brandfetch API."""

    def __init__(self, api_key: Optional[str] = None, logo_key: Optional[str] = None, brand_key: Optional[str] = None):
        """
        Initialize the Brandfetch API client.

        Args:
            api_key: Deprecated single API key (for backward compatibility)
            logo_key: Logo API key for high-quota domain lookups
            brand_key: Brand API key for brand data and searches (limited quota)
        """
        # Handle backward compatibility
        if api_key:
            logger.warning(
                "api_key is deprecated. Use logo_key and brand_key separately. "
                "Using api_key as brand_key for backward compatibility."
            )
            brand_key = brand_key or api_key

        # Load keys from environment if not provided
        self.logo_key = logo_key or os.getenv("BRANDFETCH_LOGO_KEY")
        self.brand_key = brand_key or os.getenv("BRANDFETCH_BRAND_KEY")
        
        # Validate keys with helpful error messages
        if not self.logo_key and not self.brand_key:
            raise ValueError(
                "No API keys provided. Set either:\n"
                "- BRANDFETCH_LOGO_KEY (for logo operations, high quota)\n"
                "- BRANDFETCH_BRAND_KEY (for brand/search operations, limited quota)\n"
                "- Both keys for optimal functionality"
            )

        self.base_url = "https://api.brandfetch.io/v2"
        
        # Create separate headers for each API
        self.logo_headers = {
            "Authorization": f"Bearer {self.logo_key}",
            "Accept": "application/json",
        } if self.logo_key else None
        
        self.brand_headers = {
            "Authorization": f"Bearer {self.brand_key}",
            "Accept": "application/json",
        } if self.brand_key else None

    def _normalize_domain(self, domain: str) -> str:
        """
        Validate and normalize domain input.
        
        Args:
            domain: The company domain (e.g., "github.com", "https://www.github.com")
            
        Returns:
            Normalized domain (e.g., "github.com")
            
        Raises:
            ValueError: If domain is invalid
        """
        if not domain or not isinstance(domain, str):
            raise ValueError("Domain must be a non-empty string")
        
        # Remove protocol
        domain = domain.replace("https://", "").replace("http://", "")
        
        # Remove port (e.g., localhost:3000 -> localhost)
        if ":" in domain:
            domain = domain.split(":")[0]
        
        # Remove www (case-insensitive)
        domain = domain.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        
        # Remove trailing slashes and whitespace
        domain = domain.strip().strip("/")
        
        # Basic validation
        if "." not in domain or len(domain) < 4:
            raise ValueError(f"Invalid domain format: {domain}")
        
        # Remove path if present
        if "/" in domain:
            domain = domain.split("/")[0]
        
        return domain
    
    async def get_brand(self, domain: str) -> Dict[str, Any]:
        """
        Retrieve comprehensive brand data for a domain.

        Args:
            domain: The company domain (e.g., "github.com"). Protocol and www. prefix
                    will be automatically removed if present.

        Returns:
            A dictionary containing:
                - name (str): Brand name
                - domain (str): Normalized domain
                - logos (list): Array of logo objects with URLs and formats
                - colors (list): Brand color palette with hex codes
                - fonts (list): Typography information
                - links (list): Social media profiles
                - description (str): Brand description
                - images (list): Additional brand images

        Raises:
            ValueError: If domain is invalid, brand not found, or API key is invalid
            httpx.TimeoutException: If request takes longer than 30 seconds
        """
        if not self.brand_headers:
            raise ValueError(
                "Brand API key required for brand data operations. "
                "Set BRANDFETCH_BRAND_KEY in your .env file or pass brand_key parameter."
            )
            
        domain = self._normalize_domain(domain)
        logger.info(f"Fetching brand data for domain: {domain}")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/brands/{domain}",
                    headers=self.brand_headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            
            if status == 404:
                raise ValueError(
                    f"Brand not found for domain: {domain}. "
                    f"Make sure the domain is correct and the brand exists in Brandfetch's database. "
                    f"Try searching first with search_brands to find the correct domain."
                )
            elif status == 401:
                raise ValueError(
                    f"Brand API authentication failed. Your BRANDFETCH_BRAND_KEY may be invalid or expired. "
                    f"Verify the key in your .env file. "
                    f"Get a new key at https://brandfetch.com/developers"
                )
            elif status == 429:
                raise ValueError(
                    f"Brand API rate limit exceeded. You've made too many requests to the brand API. "
                    f"Wait a few minutes before trying again. "
                    f"Consider upgrading your API plan at https://brandfetch.com/developers"
                )
            else:
                raise ValueError(
                    f"Brand API error {status}: {e.response.text}. "
                    f"This might be a temporary issue. Try again in a moment."
                )
        
        except httpx.TimeoutException:
            raise ValueError(f"Request timeout for domain: {domain}. The server took too long to respond.")
        
        except Exception as e:
            raise ValueError(f"Unexpected error fetching brand data for {domain}: {str(e)}")

    async def search_brands(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for brands by name or keyword.

        Args:
            query: Search term
            limit: Maximum number of results (not currently supported by API, kept for future use)

        Returns:
            List of brand search results

        Raises:
            ValueError: If query is invalid, API key issues, or other errors
        """
        if not query or not isinstance(query, str):
            raise ValueError("Search query must be a non-empty string")
            
        if not self.brand_headers:
            raise ValueError(
                "Brand API key required for search operations. "
                "Set BRANDFETCH_BRAND_KEY in your .env file or pass brand_key parameter."
            )
            
        logger.info(f"Searching brands for query: {query} (limit: {limit})")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/search/{query}",
                    headers=self.brand_headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                results = response.json()

                # Apply limit if results is a list
                if isinstance(results, list) and limit:
                    return results[:limit]
                return results
        
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            
            if status == 401:
                raise ValueError(
                    f"Brand API authentication failed. Your BRANDFETCH_BRAND_KEY may be invalid or expired. "
                    f"Verify the key in your .env file."
                )
            elif status == 429:
                raise ValueError(
                    f"Brand API rate limit exceeded. Wait a few minutes before trying again."
                )
            else:
                raise ValueError(
                    f"Brand API error {status} while searching brands: {e.response.text}"
                )
        
        except httpx.TimeoutException:
            raise ValueError(f"Request timeout while searching for: {query}")
        
        except Exception as e:
            raise ValueError(f"Unexpected error searching for brands: {str(e)}")

    async def get_brand_logo(
        self,
        domain: str,
        format: str = "svg",
        theme: str = "light",
        logo_type: str = "logo",
    ) -> Dict[str, Any]:
        """
        Get brand logo in specified format using the high-quota logo API first.

        This method delegates to brandfetch_logo_lookup_checked.py which reads
        BRANDFETCH_LOGO_KEY and BRANDFETCH_BRAND_KEY directly from environment
        variables. The keys passed to this client constructor are not used for
        this specific method due to the separate module's architecture.

        Args:
            domain: Company domain (protocol and www will be normalized)
            format: Desired format ('svg', 'png')
            theme: Logo theme ('light', 'dark')
            logo_type: Type of logo ('logo', 'icon', 'symbol')

        Returns:
            Logo information with URL, format, theme, type, and metadata

        Raises:
            ValueError: If domain is invalid, logo not found, or API errors
        """
        from .brandfetch_logo_lookup_checked import get_logo_for_domain
        
        domain = self._normalize_domain(domain)
        logger.info(f"Fetching {format} logo for domain: {domain} (theme: {theme}, type: {logo_type})")
        
        # Try the new logo lookup strategy first
        try:
            result = await get_logo_for_domain(domain)
            
            if "logo_url" in result:
                # Success from either domain lookup or brand API fallback
                return {
                    "url": result["logo_url"],
                    "format": format,  # Return requested format, actual may vary
                    "theme": theme,
                    "type": logo_type,
                    "source": result["source"],
                    "reason": result["reason"],
                    "brand_api_calls_this_month": result.get("brand_api_calls_this_month", 0),
                    "warning": result.get("warning"),
                }
            elif "error" in result:
                # Handle specific errors from the lookup strategy
                if result["error"] == "brand_api_limit_reached":
                    raise ValueError(
                        f"Brand API monthly limit reached ({result.get('brand_api_calls_this_month', 0)}). "
                        f"Try again next month or contact administrator."
                    )
                elif result["error"] == "no_logo_found":
                    raise ValueError(
                        f"No logos found for domain: {domain}. "
                        f"This might be because the domain doesn't exist or has no logos available."
                    )
                else:
                    raise ValueError(f"Logo lookup failed: {result.get('message', 'Unknown error')}")
                    
        except Exception as e:
            # If the new strategy fails completely, fall back to the old method
            logger.warning(f"New logo lookup failed for {domain}, falling back to brand API: {e}")
            
            try:
                brand_data = await self.get_brand(domain)
            except ValueError as fallback_error:
                # Re-raise domain/API errors with context
                raise ValueError(f"Cannot fetch logo: {str(fallback_error)}")
                
            logos = brand_data.get("logos", [])

            # Find matching logo
            for logo in logos:
                if logo.get("type") == logo_type and logo.get("theme") == theme:
                    formats = logo.get("formats", [])
                    for fmt in formats:
                        if fmt.get("format") == format:
                            return {
                                "url": fmt.get("src"),
                                "format": format,
                                "theme": theme,
                                "type": logo_type,
                                "metadata": fmt,
                                "source": "brand_api_fallback",
                                "reason": "New lookup strategy failed, used full Brand API",
                            }

            # If exact match not found, return first available with helpful note
            if logos and logos[0].get("formats"):
                first_format = logos[0]["formats"][0]
                available_types = [logo.get("type") for logo in logos]
                available_themes = list(set(logo.get("theme") for logo in logos))
                
                return {
                    "url": first_format.get("src"),
                    "format": first_format.get("format"),
                    "theme": logos[0].get("theme"),
                    "type": logos[0].get("type"),
                    "metadata": first_format,
                    "source": "brand_api_fallback",
                    "reason": "New lookup strategy failed, used full Brand API fallback",
                    "note": f"Requested format ({format}, {theme}, {logo_type}) not found. "
                           f"Returned first available. Available types: {available_types}, "
                           f"themes: {available_themes}",
                }

            raise ValueError(
                f"No logos found for domain: {domain}. "
                f"This brand might not have any logos in Brandfetch's database."
            )

    async def get_brand_colors(self, domain: str) -> List[Dict[str, Any]]:
        """
        Extract brand color palette.

        Args:
            domain: Company domain (protocol and www will be normalized)

        Returns:
            List of brand colors with hex codes, types, and brightness metadata

        Raises:
            ValueError: If domain is invalid, colors not found, or API errors
        """
        if not self.brand_headers:
            raise ValueError(
                "Brand API key required for color operations. "
                "Set BRANDFETCH_BRAND_KEY in your .env file or pass brand_key parameter."
            )
            
        domain = self._normalize_domain(domain)
        logger.info(f"Fetching brand colors for domain: {domain}")
        
        try:
            brand_data = await self.get_brand(domain)
        except ValueError as e:
            # Re-raise domain/API errors with context
            raise ValueError(f"Cannot fetch colors: {str(e)}")
            
        colors = brand_data.get("colors", [])

        if not colors:
            raise ValueError(
                f"No colors found for domain: {domain}. "
                f"This brand might not have color information in Brandfetch's database."
            )

        return colors
