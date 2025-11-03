# Changelog

All notable changes to the Brandfetch MCP Server will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-11-01

### ⚠️ BREAKING CHANGES
- **API Key Structure**: Changed from single `BRANDFETCH_API_KEY` to separate keys:
  - `BRANDFETCH_CLIENT_ID`: For logo operations (high quota) and client ID for hotlinking compliance
  - `BRANDFETCH_API_KEY`: For brand data and searches (limited quota)
- **Client Constructor**: Now accepts `logo_key` and `brand_key` parameters
- **Deprecated**: `api_key` parameter is deprecated but still supported for backward compatibility

### Added
- Separate API key support for different Brandfetch endpoints
- Improved error messages that specify which API key is missing
- Backward compatibility layer with deprecation warnings
- Better quota management by using appropriate keys for each operation

### Changed
- `get_brand()` method now requires `BRANDFETCH_API_KEY`
- `search_brands()` method now requires `BRANDFETCH_API_KEY`
- `get_brand_colors()` method now requires `BRANDFETCH_API_KEY`
- `brand_logo.py` module updated to support new key pattern with fallback
- Relative path loading for `.env` file with `override=False` for testability

### Deprecated
- `BRANDFETCH_API_KEY` environment variable (removed in v0.2.1)
- `api_key` parameter in `BrandfetchClient.__init__()` (will be removed in v1.0.0)

### Fixed
- Test isolation issues with environment variable mocking
- Error message specificity for different API endpoints

### Known Issues
- Some get_brand_logo tests mock wrong layer (functionality works, tests need updating)
- `.env` path resolution only works in development mode, not pip-installed packages

### Migration Guide
```bash
# Old way (removed)
# export BRANDFETCH_API_KEY="your_key_here"

# New way (recommended)
export BRANDFETCH_CLIENT_ID="your_logo_key_here"
export BRANDFETCH_API_KEY="your_brand_key_here"

# Or in .env file
BRANDFETCH_CLIENT_ID=your_logo_key_here
BRANDFETCH_API_KEY=your_brand_key_here
```

### Security
- API key loaded from environment variables only
- No API key logging

## [0.1.0] - 2025-10-31

### Added
- Initial release
- Core MCP server implementation
- Support for stdio transport
- Integration with Claude Desktop

[Unreleased]: https://github.com/yourusername/brandfetch_mcp/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/yourusername/brandfetch_mcp/releases/tag/v0.1.0
