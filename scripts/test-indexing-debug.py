#!/usr/bin/env python3
"""Debug the indexing script's structured data extraction"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from index_kismet_site import extract_page_content
import asyncio
import aiohttp

async def test():
    print("Fetching https://www.makekismet.com/...")
    async with aiohttp.ClientSession() as session:
        async with session.get('https://www.makekismet.com/', ssl=False) as response:
            html = await response.text()
    
    print("Extracting page content...")
    result = await extract_page_content(html)
    
    print(f"\nFound {len(result['structured_data'])} structured data items")
    for i, sd in enumerate(result['structured_data']):
        if isinstance(sd, dict):
            print(f"\nStructured data item {i+1}:")
            print(f"  Type: {sd.get('@type')}")
            if sd.get('@type') == 'FAQPage':
                print(f"  FAQPage has {len(sd.get('mainEntity', []))} questions!")
                for j, q in enumerate(sd.get('mainEntity', [])[:3]):
                    print(f"    Q{j+1}: {q.get('name', 'No question')}")

if __name__ == "__main__":
    asyncio.run(test()) 