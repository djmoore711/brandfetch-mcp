#!/usr/bin/env python3
"""Manual test script for Brandfetch API client.

This script tests the API client with real API calls.
Requires BRANDFETCH_LOGO_KEY and/or BRANDFETCH_BRAND_KEY to be set in .env file.

Usage:
    python manual_test.py
"""

import asyncio
import json
from brandfetch_mcp.client import BrandfetchClient


async def test_get_brand():
    """Test get_brand with real API."""
    print("\n" + "="*60)
    print("Testing get_brand (github.com)")
    print("="*60)
    
    try:
        client = BrandfetchClient()
        result = await client.get_brand("github.com")
        
        print(f"✓ Success!")
        print(f"  Brand: {result.get('name')}")
        print(f"  Domain: {result.get('domain')}")
        print(f"  Description: {result.get('description', 'N/A')[:100]}...")
        print(f"  Logos: {len(result.get('logos', []))} available")
        print(f"  Colors: {len(result.get('colors', []))} available")
        print(f"  Fonts: {len(result.get('fonts', []))} available")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_search_brands():
    """Test search_brands with real API."""
    print("\n" + "="*60)
    print("Testing search_brands (query: coffee)")
    print("="*60)
    
    try:
        client = BrandfetchClient()
        results = await client.search_brands("coffee", limit=5)
        
        print(f"✓ Success! Found {len(results)} results:")
        for i, brand in enumerate(results[:5], 1):
            print(f"  {i}. {brand.get('name', 'Unknown')} ({brand.get('domain', 'N/A')})")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_get_brand_logo():
    """Test get_brand_logo with real API."""
    print("\n" + "="*60)
    print("Testing get_brand_logo (stripe.com, SVG)")
    print("="*60)
    
    try:
        client = BrandfetchClient()
        logo = await client.get_brand_logo("stripe.com", format="svg", theme="light")
        
        print(f"✓ Success!")
        print(f"  URL: {logo['url'][:60]}...")
        print(f"  Format: {logo['format']}")
        print(f"  Theme: {logo['theme']}")
        print(f"  Type: {logo['type']}")
        
        if 'note' in logo:
            print(f"  Note: {logo['note']}")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_get_brand_colors():
    """Test get_brand_colors with real API."""
    print("\n" + "="*60)
    print("Testing get_brand_colors (netflix.com)")
    print("="*60)
    
    try:
        client = BrandfetchClient()
        colors = await client.get_brand_colors("netflix.com")
        
        print(f"✓ Success! Found {len(colors)} colors:")
        for color in colors[:5]:
            hex_code = color.get('hex', 'N/A')
            color_type = color.get('type', 'unknown')
            brightness = color.get('brightness', 'N/A')
            print(f"  {hex_code} ({color_type}, brightness: {brightness})")
        
        return True
    except Exception as e:
        print(f"✗ Error: {e}")
        return False


async def test_error_handling():
    """Test error handling with invalid domain."""
    print("\n" + "="*60)
    print("Testing error handling (invalid domain)")
    print("="*60)
    
    try:
        client = BrandfetchClient()
        await client.get_brand("this-domain-definitely-does-not-exist-12345.com")
        
        print(f"✗ Should have raised an error!")
        return False
    except Exception as e:
        print(f"✓ Correctly raised error: {type(e).__name__}")
        print(f"  Message: {str(e)[:100]}")
        return True


async def main():
    """Run all manual tests."""
    print("\n" + "#"*60)
    print("# Brandfetch API Client - Manual Test Suite")
    print("#"*60)
    
    results = []
    
    # Run tests
    results.append(("get_brand", await test_get_brand()))
    results.append(("search_brands", await test_search_brands()))
    results.append(("get_brand_logo", await test_get_brand_logo()))
    results.append(("get_brand_colors", await test_get_brand_colors()))
    results.append(("error_handling", await test_error_handling()))
    
    # Summary
    print("\n" + "#"*60)
    print("# Test Summary")
    print("#"*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
