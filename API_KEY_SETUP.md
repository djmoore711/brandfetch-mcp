# Brandfetch API Key Setup

## Step 1: Get Your API Keys
1. Go to [Brandfetch Developers Portal](https://brandfetch.com/developers)
2. Create two separate API keys:
   - One for **Logo API** (high quota)
   - One for **Brand API** (limited quota)

## Step 2: Configure Your .env File
Create a `.env` file in the project root with:
```env
# Brandfetch API Configuration
BRANDFETCH_LOGO_KEY="paste_logo_key_here"
BRANDFETCH_BRAND_KEY="paste_brand_key_here"
```
