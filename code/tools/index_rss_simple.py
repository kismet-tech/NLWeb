#!/usr/bin/env python3
"""
Simple RSS feed indexer for Qdrant that works with Python 3.9
"""

import os
import sys
import feedparser
from datetime import datetime
import json
from typing import List, Dict, Any
from urllib.parse import urlparse
import uuid
import xml.etree.ElementTree as ET
import requests

# Import required libraries
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct
from openai import OpenAI

# Initialize clients
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
qdrant_client = QdrantClient(
    url=os.environ.get("QDRANT_URL"),
    api_key=os.environ.get("QDRANT_API_KEY")
)

COLLECTION_NAME = "nlweb_collection"
EMBEDDING_MODEL = "text-embedding-3-small"
VECTOR_DIM = 1536

def get_embedding(text: str) -> List[float]:
    """Get embedding for text using OpenAI"""
    response = openai_client.embeddings.create(
        input=text,
        model=EMBEDDING_MODEL
    )
    return response.data[0].embedding

def parse_rss_manually(feed_url: str) -> List[Dict[str, Any]]:
    """Manually parse RSS XML when feedparser fails"""
    try:
        response = requests.get(feed_url)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = []
        
        # Find all item elements
        for item in root.findall('.//item'):
            entry = {}
            entry['title'] = item.findtext('title', '')
            entry['link'] = item.findtext('link', '')
            entry['description'] = item.findtext('description', '')
            entry['pubDate'] = item.findtext('pubDate', '')
            
            # Try to get content:encoded
            content_ns = {'content': 'http://purl.org/rss/1.0/modules/content/'}
            content_encoded = item.findtext('content:encoded', '', content_ns)
            if content_encoded:
                entry['content'] = content_encoded
            
            items.append(entry)
        
        return items
    except Exception as e:
        print(f"Error manually parsing RSS: {e}")
        return []

def process_rss_feed(feed_url: str, site_name: str) -> List[Dict[str, Any]]:
    """Process RSS feed and extract content"""
    feed = feedparser.parse(feed_url)
    documents = []
    
    # Debug output
    print(f"Feed status: {feed.get('status', 'N/A')}")
    print(f"Feed title: {feed.feed.get('title', 'N/A') if hasattr(feed, 'feed') else 'No feed object'}")
    print(f"Number of entries: {len(feed.entries) if hasattr(feed, 'entries') else 0}")
    
    entries = feed.entries if hasattr(feed, 'entries') and len(feed.entries) > 0 else []
    
    # If feedparser didn't find entries, try manual parsing
    if len(entries) == 0:
        print("Feedparser found no entries, trying manual XML parsing...")
        manual_entries = parse_rss_manually(feed_url)
        if manual_entries:
            print(f"Manual parsing found {len(manual_entries)} entries")
            for entry in manual_entries:
                title = entry.get('title', '')
                link = entry.get('link', '')
                content = entry.get('content', entry.get('description', ''))
                published = entry.get('pubDate', '')
                
                # Clean up content if it contains HTML
                if content.startswith('<![CDATA['):
                    content = content[9:-3]  # Remove CDATA wrapper
                
                text_content = f"{title}\n\n{content}"
                
                doc = {
                    'name': title,
                    'url': link,
                    'site': site_name,
                    'text': text_content,
                    'schema_json': json.dumps({
                        'title': title,
                        'summary': content,
                        'published': published,
                        'link': link
                    })
                }
                documents.append(doc)
                print(f"Added document: {title}")
        else:
            # Fall back to creating a single document from feed info
            if hasattr(feed, 'feed'):
                print("No entries found, creating document from feed info")
                doc = {
                    'name': feed.feed.get('title', 'Kismet Homepage'),
                    'url': feed.feed.get('link', 'https://www.makekismet.com'),
                    'site': site_name,
                    'text': f"{feed.feed.get('title', 'Kismet')}\n\n{feed.feed.get('description', '')}",
                    'schema_json': json.dumps({
                        'title': feed.feed.get('title', 'Kismet Homepage'),
                        'summary': feed.feed.get('description', ''),
                        'published': '',
                        'link': feed.feed.get('link', 'https://www.makekismet.com')
                    })
                }
                documents.append(doc)
    else:
        print(f"Processing {len(entries)} entries from {feed_url}")
        
        for entry in entries:
            # Extract content
            title = entry.get('title', '')
            link = entry.get('link', '')
            summary = entry.get('description', entry.get('summary', ''))
            published = entry.get('published', entry.get('pubDate', ''))
            
            # Also check for content:encoded
            content = entry.get('content', [])
            if content and len(content) > 0:
                full_content = content[0].get('value', summary)
            else:
                full_content = summary
            
            # Create combined text for embedding
            text_content = f"{title}\n\n{full_content}"
            
            # Create document
            doc = {
                'name': title,
                'url': link,
                'site': site_name,
                'text': text_content,
                'schema_json': json.dumps({
                    'title': title,
                    'summary': full_content,
                    'published': published,
                    'link': link
                })
            }
            documents.append(doc)
            print(f"Added document: {title}")
        
    return documents

def index_documents(documents: List[Dict[str, Any]]):
    """Index documents into Qdrant"""
    points = []
    
    for i, doc in enumerate(documents):
        print(f"Processing document {i+1}/{len(documents)}: {doc['name'][:50]}...")
        
        # Get embedding
        embedding = get_embedding(doc['text'])
        
        # Create unique ID
        doc_id = str(uuid.uuid4())
        
        # Create point
        point = PointStruct(
            id=doc_id,
            vector=embedding,
            payload={
                'name': doc['name'],
                'url': doc['url'],
                'site': doc['site'],
                'text': doc['text'],
                'schema_json': doc['schema_json']
            }
        )
        points.append(point)
    
    # Upload to Qdrant
    print(f"Uploading {len(points)} points to Qdrant...")
    qdrant_client.upsert(
        collection_name=COLLECTION_NAME,
        points=points
    )
    print("Upload complete!")

def main():
    if len(sys.argv) != 3:
        print("Usage: python index_rss_simple.py <feed_url> <site_name>")
        sys.exit(1)
    
    feed_url = sys.argv[1]
    site_name = sys.argv[2]
    
    # Check environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        sys.exit(1)
    if not os.environ.get("QDRANT_URL"):
        print("Error: QDRANT_URL environment variable not set")
        sys.exit(1)
    if not os.environ.get("QDRANT_API_KEY"):
        print("Error: QDRANT_API_KEY environment variable not set")
        sys.exit(1)
    
    # Process and index
    documents = process_rss_feed(feed_url, site_name)
    print(f"Found {len(documents)} documents to index")
    
    if documents:
        index_documents(documents)
    else:
        print("No documents found to index")

if __name__ == "__main__":
    main() 