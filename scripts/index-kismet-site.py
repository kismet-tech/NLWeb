#!/usr/bin/env python3
"""
Script to automatically index Kismet website content into NLWeb.
Reads from sitemap.xml and creates JSON data for indexing.
"""

import asyncio
import aiohttp
import json
import os
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Dict, List, Any
from bs4 import BeautifulSoup
import re

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

# Import db_load functionality
from tools.db_load import loadJsonToDB, delete_site_from_database

SITE_NAME = "makekismet"
SITEMAP_URL = "https://www.makekismet.com/sitemap.xml"
SITE_BASE_URL = "https://www.makekismet.com"

# Known structured data URLs from nlweb.json
STRUCTURED_URLS = [
    {
        "url": "https://www.makekismet.com/",
        "@type": "FAQPage"
    },
    {
        "url": "https://www.makekismet.com/resources/Kismet_teaser_v2.1_20250523.pdf",
        "@type": "PresentationDigitalDocument"
    },
    {
        "url": "https://www.makekismet.com/resources/direct-to-guest-ai-teaser",
        "@type": "WebPage"
    },
    {
        "url": "https://www.makekismet.com/",
        "@type": "SoftwareApplication"
    }
]

async def fetch_url_content(session: aiohttp.ClientSession, url: str) -> str:
    """Fetch content from a URL."""
    try:
        async with session.get(url, timeout=30) as response:
            if response.status == 200:
                return await response.text()
            else:
                print(f"Failed to fetch {url}: HTTP {response.status}")
                return ""
    except Exception as e:
        print(f"Error fetching {url}: {str(e)}")
        return ""

async def extract_page_content(html: str) -> Dict[str, Any]:
    """Extract relevant content from HTML page."""
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract metadata
    title = ""
    description = ""
    
    # Try to get title
    title_tag = soup.find('title')
    if title_tag:
        title = title_tag.get_text(strip=True)
    
    # Try to get meta description
    meta_desc = soup.find('meta', attrs={'name': 'description'})
    if meta_desc:
        description = meta_desc.get('content', '')
    
    # Extract main content
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Get text content
    text_content = soup.get_text()
    # Clean up whitespace
    lines = (line.strip() for line in text_content.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text_content = ' '.join(chunk for chunk in chunks if chunk)
    
    # Look for JSON-LD structured data
    json_ld_scripts = soup.find_all('script', type='application/ld+json')
    structured_data = []
    for script in json_ld_scripts:
        try:
            data = json.loads(script.string)
            structured_data.append(data)
        except:
            pass
    
    return {
        "title": title,
        "description": description,
        "text": text_content[:5000],  # Limit text length
        "structured_data": structured_data
    }

async def fetch_sitemap(session: aiohttp.ClientSession) -> List[str]:
    """Fetch and parse sitemap to get URLs."""
    sitemap_content = await fetch_url_content(session, SITEMAP_URL)
    if not sitemap_content:
        print("Failed to fetch sitemap")
        return []
    
    urls = []
    try:
        root = ET.fromstring(sitemap_content)
        # Handle namespace in sitemap
        namespace = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        
        for url_elem in root.findall('.//sm:url/sm:loc', namespace):
            urls.append(url_elem.text)
    except Exception as e:
        print(f"Error parsing sitemap: {str(e)}")
    
    return urls

async def create_nlweb_documents(urls: List[str]) -> List[Dict[str, Any]]:
    """Create NLWeb-compatible documents from URLs."""
    documents = []
    
    async with aiohttp.ClientSession() as session:
        for url in urls:
            print(f"Processing {url}...")
            
            # Skip PDF files
            if url.endswith('.pdf'):
                # Add PDF as a document
                documents.append({
                    "url": url,
                    "name": "Kismet Direct-to-Guest AI Teaser PDF",
                    "@type": "PresentationDigitalDocument",
                    "description": "Discover how Kismet's Direct-to-Guest AI helps hotels turn chat, social, web, ads, email and SMS into personal itineraries guests can book instantly.",
                    "site": SITE_NAME
                })
                continue
            
            # Fetch and process HTML pages
            html_content = await fetch_url_content(session, url)
            if html_content:
                page_data = await extract_page_content(html_content)
                
                # Create base document
                doc = {
                    "url": url,
                    "name": page_data["title"] or f"Page at {url}",
                    "description": page_data["description"],
                    "text": page_data["text"],
                    "site": SITE_NAME
                }
                
                # Add type information if available
                for struct_url in STRUCTURED_URLS:
                    if struct_url["url"] == url:
                        doc["@type"] = struct_url["@type"]
                        break
                else:
                    doc["@type"] = "WebPage"  # Default type
                
                # If we found structured data, merge it
                if page_data["structured_data"]:
                    for sd in page_data["structured_data"]:
                        if isinstance(sd, dict):
                            # Merge relevant fields
                            for key in ["@type", "mainEntity", "offers", "publisher"]:
                                if key in sd and key not in doc:
                                    doc[key] = sd[key]
                
                documents.append(doc)
            
            # Small delay to be respectful
            await asyncio.sleep(0.5)
    
    # Add FAQ content directly (since it's embedded in the homepage)
    faq_document = {
        "url": "https://www.makekismet.com/#faq",
        "name": "Kismet Frequently Asked Questions",
        "@type": "FAQPage",
        "site": SITE_NAME,
        "mainEntity": [
            {
                "@type": "Question",
                "name": "What is Kismet?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Kismet is Direct-to-Guest AI for hotels. We help hotels identify each prospective guest, craft personal itineraries and convert them with one-tap booking across chat, social, web, ads, email and SMS."
                }
            },
            {
                "@type": "Question", 
                "name": "How does Kismet work?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "Kismet uses AI to engage with prospective guests across all channels. We identify guests, understand their preferences, create personalized offers, and enable instant booking—all while learning what works best for your hotel."
                }
            },
            {
                "@type": "Question",
                "name": "What channels does Kismet support?",
                "acceptedAnswer": {
                    "@type": "Answer", 
                    "text": "Kismet works across live chat, Instagram, your website, digital ads, email, and SMS. We unify all these channels into one seamless guest experience."
                }
            },
            {
                "@type": "Question",
                "name": "How quickly can I get started?",
                "acceptedAnswer": {
                    "@type": "Answer",
                    "text": "You can go Direct-to-Guest in less than a month—no new booking engine required. Book a 20-minute discovery call to learn more."
                }
            }
        ]
    }
    documents.append(faq_document)
    
    return documents

async def save_documents_to_file(documents: List[Dict[str, Any]], filename: str):
    """Save documents to a JSON file in the format expected by db_load."""
    output_lines = []
    
    for doc in documents:
        # Create URL and JSON parts
        url = doc.get("url", "")
        # Remove URL from the document to avoid duplication
        doc_copy = doc.copy()
        if "url" in doc_copy:
            del doc_copy["url"]
        
        json_str = json.dumps(doc_copy, ensure_ascii=False)
        
        # Format: URL<TAB>JSON
        output_lines.append(f"{url}\t{json_str}")
    
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write('\n'.join(output_lines))
    
    print(f"Saved {len(documents)} documents to {filename}")

async def main():
    """Main function to orchestrate the indexing process."""
    print(f"Starting Kismet website indexing at {datetime.now()}")
    
    # Fetch sitemap URLs
    async with aiohttp.ClientSession() as session:
        urls = await fetch_sitemap(session)
    
    if not urls:
        print("No URLs found in sitemap")
        return
    
    print(f"Found {len(urls)} URLs in sitemap")
    
    # Create NLWeb documents
    documents = await create_nlweb_documents(urls)
    
    print(f"Created {len(documents)} documents")
    
    # Save to temporary file
    temp_file = "/tmp/kismet_website_data.json"
    await save_documents_to_file(documents, temp_file)
    
    # Delete existing data for the site
    print(f"Deleting existing data for site '{SITE_NAME}'...")
    try:
        await delete_site_from_database(SITE_NAME)
    except Exception as e:
        print(f"Warning: Could not delete existing data: {e}")
    
    # Load new data into NLWeb
    print(f"Loading data into NLWeb...")
    try:
        await loadJsonToDB(
            file_path=temp_file,
            site=SITE_NAME,
            batch_size=100,
            delete_existing=False,  # We already deleted
            force_recompute=True
        )
        print("Successfully indexed Kismet website!")
    except Exception as e:
        print(f"Error loading data into NLWeb: {e}")
        raise
    
    # Clean up temp file
    try:
        os.remove(temp_file)
    except:
        pass

if __name__ == "__main__":
    asyncio.run(main()) 