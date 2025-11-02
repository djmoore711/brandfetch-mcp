# Brandfetch MCP Server Specification

## Purpose
Create an MCP server that exposes Brandfetch API capabilities as MCP tools.

## Required Tools
1. get_brand_details - Retrieve comprehensive brand information
2. search_brands - Search for brands by name
3. get_brand_logo - Fetch brand logos in specified format
4. get_brand_colors - Extract brand color palette

## Environment Variables
- BRANDFETCH_LOGO_KEY: API key for logo-by-domain endpoints (high quota)
- BRANDFETCH_BRAND_KEY: API key for brand details and search endpoints (limited quota)

See full documentation in API_REFERENCE.md
