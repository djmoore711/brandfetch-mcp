# Brandfetch API Key Setup

## Required Keys

1. **Client ID** (for hotlinking compliance, optional but recommended)
2. **Brand API Key** (limited quota, for fallback searches)

## How to Get Keys

### Client ID
1. Go to https://brandfetch.com/developers
2. Sign up or log in
3. Click "Logo API" and then "Overview"
4. Copy your Client ID
![Client ID Setup](images/brandfetch_get_client_id_logo_api.png)

### Brand API Keys
1. Go to https://brandfetch.com/developers
2. Sign up or log in
3. Click "Brand API" and then "Overview"
4. Copy your API key
![Brand API Key Setup](images/brandfetch_get_api_key_brand_api.png)

## Add to .env
```bash
BRANDFETCH_CLIENT_ID="paste_logo_key_here"
BRANDFETCH_API_KEY="paste_brand_key_here"
```
