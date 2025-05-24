#!/usr/bin/env python3
"""Test script to debug FAQ extraction"""

import requests
from bs4 import BeautifulSoup
import json

def test_faq_extraction():
    response = requests.get("https://www.makekismet.com/")
    html = response.text
    
    soup = BeautifulSoup(html, 'html.parser')
    
    # Find all script tags with type application/ld+json
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    
    print(f"Found {len(json_ld_scripts)} JSON-LD script tags")
    
    for i, script in enumerate(json_ld_scripts):
        try:
            data = json.loads(script.string)
            print(f"\nScript {i+1}:")
            print(f"  Type: {data.get('@type', 'Unknown')}")
            if data.get('@type') == 'FAQPage':
                print(f"  Found FAQPage with {len(data.get('mainEntity', []))} questions!")
                for j, q in enumerate(data.get('mainEntity', [])[:5]):
                    print(f"    Q{j+1}: {q.get('name', 'No name')}")
                print(f"    ... and {len(data.get('mainEntity', [])) - 5} more questions")
        except Exception as e:
            print(f"  Error parsing: {e}")
            if script.string:
                print(f"  Content preview: {script.string[:100]}...")

if __name__ == "__main__":
    test_faq_extraction() 