# Brandfetch API Key Setup

## Required Keys

1. **Logo API Key** (high quota, for domain lookups)
2. **Brand API Key** (limited quota, for fallback searches)
3. **Client ID** (for hotlinking compliance, optional but recommended)

## How to Get Keys

### Logo and Brand API Keys
1. Go to https://brandfetch.com/developers
2. Sign up or log in
3. Generate both keys from your dashboard

### Client ID
1. Go to https://developers.brandfetch.com/register
2. Register your application
3. Get your client ID for hotlinking compliance

## Add to .env

```bash
BRANDFETCH_LOGO_KEY="paste_logo_key_here"
BRANDFETCH_BRAND_KEY="paste_brand_key_here"
BRANDFETCH_CLIENT_ID="paste_client_id_here"
