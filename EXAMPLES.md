# Brandfetch MCP Server - Usage Examples

## Claude Desktop Queries

### Getting Brand Information
```
"Get brand details for github.com"
"Show me information about the Stripe brand"
"What can you tell me about netflix.com's branding?"
```

### Searching for Brands
```
"Search for coffee brands"
"Find brands related to 'technology'"
"Show me fashion brands"
"Search for payment companies"
```

### Getting Logos
```
"Get the SVG logo for github.com"
"Find the dark theme logo for stripe.com"
"Show me the icon for netflix.com"
"Get a PNG logo for apple.com"
```

### Getting Colors
```
"What colors does github.com use?"
"Show me the color palette for stripe.com"
"What are netflix's brand colors?"
"Get the brand colors for spotify.com"
```

### Complex Queries
```
"Get the brand details for stripe.com and show me their color palette"
"Search for coffee brands and get the logo for the top result"
"Compare the colors of github.com and gitlab.com"
```

## Expected Response Format

The server returns clean, readable markdown like this:

### Brand Details Example
```
# GitHub (github.com)

**Description:** GitHub provides code hosting services that allow developers/people to build software...

**Company Details:**
  - Employees: 501
  - Founded: 2008
  - Location: San Francisco, United States

**Available Logos:** 5
  - logo (light, png): https://cdn.brandfetch.io/... (31,120 bytes)
  - symbol (light, svg): https://cdn.brandfetch.io/... (960 bytes)
  - ... and 3 more

**Brand Colors:**
  - #6E40C9 (accent, brightness: 84)
  - #24292E (dark, brightness: 40)
  - #FAFBFC (brand, brightness: 251)
  - ... and 2 more

**Typography:**
  - system-ui (title, system)
  - system-ui (body, system)

**Social Media:**
  - crunchbase: https://crunchbase.com/organization/github
  - youtube: https://youtube.com/github
  - github: https://github.com/github.com
  - ... and 4 more

**Brand Status:** Unclaimed
**Quality Score:** 96.15%
```

### Search Results Example
```
Found 5 brands:

1. **Atlas Coffee Club** (atlascoffeeclub.com) - Unclaimed
   Premium coffee subscription service delivering fresh roasted...

2. **Dutch Bros Coffee** (dutchbros.com) - ✓ Claimed
   Drive-thru coffee chain known for friendly service and...

3. **Black Rifle Coffee** (blackriflecoffee.com) - ✓ Claimed
   Veteran-owned coffee company supporting veterans...

4. **Blue Bottle Coffee** (bluebottlecoffee.com) - ✓ Claimed
   Premium coffee roaster focused on quality and...

5. **The Coffee Bean & Tea Leaf** (coffeebean.com) - ✓ Claimed
   Global coffee and tea retailer with a wide range of...
```

### Logo Response Example
```
**Logo URL:** https://cdn.brandfetch.io/idxAg10C0L/theme/light/logo.svg?c=paste_logo_key

**Format:** svg
**Theme:** light
**Type:** logo

**Details:**
  - Size: 2,456 bytes
  - Dimensions: 208x44px
  - Background: transparent
```

### Color Palette Example
```
**Brand Color Palette:** 5 colors

**Brand Colors:**
  • #FAFBFC (brightness: 251)
  • #1B7F38 (brightness: 101)

**Accent Colors:**
  • #6E40C9 (brightness: 84)

**Dark Colors:**
  • #24292E (brightness: 40)

**Light Colors:**
  • #FFFFFF (brightness: 255)
```

## Error Handling Examples

The server provides clear, actionable error messages:

```
❌ Error: Brand not found for domain: invalid-domain.com. 
Make sure the domain is correct and the brand exists in Brandfetch's database. 
Try searching first with search_brands to find the correct domain.
```

```
❌ Error: Authentication failed. Your API key may be invalid or expired. 
Verify BRANDFETCH_CLIENT_ID and BRANDFETCH_API_KEY in your .env file. 
Get new keys at https://brandfetch.com/developers
```

## Tips for Best Results

1. **Use clean domain names** - The server automatically handles http://, https://, www, and paths
2. **Search first if unsure** - Use search_brands to find the correct domain for a company
3. **Specify logo preferences** - Use format, theme, and type parameters for specific logos
4. **Check error messages** - They provide helpful guidance for fixing issues

## Integration with Claude Desktop

1. Configure your Claude Desktop per QUICKSTART.md
2. The server will appear as available tools (look for the 🔨 icon)
3. Use any of the example queries above
4. Responses will be formatted as clean markdown for easy reading

---

All examples tested and working with the current implementation!
