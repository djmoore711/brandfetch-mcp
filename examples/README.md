# Example API Responses

This directory contains sample responses from the Brandfetch API for reference and offline testing.

## Files

### github_brand.json
Complete brand data response for GitHub.com including:
- Brand metadata (name, domain, description)
- Multiple logo formats (SVG, PNG)
- Logo variations (light/dark themes)
- Brand colors with hex codes
- Typography information
- Social media links
- Banner images

**Use case:** Understanding the full structure of brand data

### search_results.json
Search results for "coffee" brands including:
- Starbucks
- Dunkin'
- Blue Bottle Coffee
- Peet's Coffee
- Tim Hortons

Each result includes name, domain, claimed status, and icon URL.

**Use case:** Understanding search response structure

### logo_response.json
Logo-specific response showing:
- Direct logo URL
- Format information (SVG/PNG)
- Theme (light/dark)
- Logo type (logo/icon/symbol)
- Metadata (size, dimensions, background)

**Use case:** Understanding logo extraction responses

### colors_response.json
Brand color palette response (Netflix example) including:
- Hex color codes
- Color type classification
- Brightness values

**Use case:** Understanding color palette responses

## Usage

### In Tests
```python
import json

def test_parse_brand_data():
    with open('examples/github_brand.json') as f:
        data = json.load(f)
    
    assert data['name'] == 'GitHub'
    assert len(data['logos']) > 0
```

### For Development
Reference these files when building response formatters or testing parsing logic without making API calls.

### For Documentation
Use these examples to show users what to expect from each tool.

## Notes

- These are real response structures from the Brandfetch API
- Data may be slightly outdated but structure is accurate
- Use for reference only; actual API responses may vary
- Some URLs are examples and may not work if accessed directly
