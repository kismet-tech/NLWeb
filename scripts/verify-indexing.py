#!/usr/bin/env python3
"""
Script to verify what content is actually indexed in the vector database.
This helps diagnose why certain queries aren't returning results.
"""

import asyncio
import json
import os
import sys
from typing import List, Dict, Any

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from retrieval.retriever import VectorDBClient

SITE_NAME = "makekismet"

async def verify_indexed_content():
    """Verify what's actually in the vector database."""
    
    print(f"Verifying indexed content for site '{SITE_NAME}'...")
    
    # Initialize the vector DB client
    client = VectorDBClient()
    
    # Search for specific FAQ content
    test_queries = [
        "How do I make sure AI can find my hotel?",
        "How does Kismet increase direct bookings?",
        "Does Kismet replace my booking engine?",
        "What is Direct-to-Guest AI?",
        "Email Dashboard",
        "Marketing Lists"
    ]
    
    print("\n" + "="*80)
    print("TESTING SPECIFIC QUERIES")
    print("="*80)
    
    for query in test_queries:
        print(f"\nQuery: '{query}'")
        print("-" * 40)
        
        try:
            # Search for the query
            results = await client.search(
                query=query,
                site=SITE_NAME,
                num_results=3
            )
            
            if results:
                print(f"Found {len(results)} results:")
                for i, result in enumerate(results[:3], 1):
                    print(f"\n  Result {i}:")
                    # Results are typically lists with format [url, description, site, metadata]
                    if len(result) >= 3:
                        print(f"  - URL: {result[0]}")
                        print(f"  - Site: {result[2]}")
                        if len(result) > 1:
                            content_snippet = str(result[1])[:200] + "..." if len(str(result[1])) > 200 else str(result[1])
                            print(f"  - Content: {content_snippet}")
                        if len(result) > 3:
                            print(f"  - Metadata: {result[3]}")
            else:
                print("  ❌ NO RESULTS FOUND")
                
        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
    
    # Get total count by searching with empty query
    print("\n" + "="*80)
    print("DOCUMENT STATISTICS")
    print("="*80)
    
    try:
        # Search with generic query to get sample documents
        all_results = await client.search(
            query="",  # Empty query to get all
            site=SITE_NAME,
            num_results=100  # Get up to 100 documents
        )
        
        if all_results:
            print(f"\nFound approximately {len(all_results)} documents (up to 100 shown)")
            
            # Show some examples
            print("\nSample documents:")
            for i, result in enumerate(all_results[:5], 1):
                print(f"\n  Document {i}:")
                if len(result) >= 1:
                    print(f"  - URL: {result[0]}")
                if len(result) >= 3:
                    print(f"  - Site: {result[2]}")
            
            # Check for FAQs
            faq_count = 0
            sales_faq_count = 0
            for result in all_results:
                if len(result) >= 1:
                    url = str(result[0])
                    if "#faq" in url or "FAQ:" in str(result[1] if len(result) > 1 else ""):
                        faq_count += 1
                        if "sales" in url:
                            sales_faq_count += 1
            
            print(f"\nFAQ statistics:")
            print(f"  - Total FAQ documents found: {faq_count}")
            print(f"  - Sales FAQ documents found: {sales_faq_count}")
            
        else:
            print("❌ No documents found in the database!")
            
    except Exception as e:
        print(f"❌ ERROR getting document statistics: {str(e)}")

async def check_connection():
    """Check if we can connect to the vector database."""
    print("Checking database connection...")
    
    try:
        client = VectorDBClient()
        # Try a simple search
        results = await client.search(
            query="test",
            site=SITE_NAME,
            num_results=1
        )
        print("✅ Database connection successful")
        return True
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

async def main():
    """Main verification function."""
    print(f"Vector Database Verification Tool")
    print(f"Site: {SITE_NAME}")
    print(f"Database: {os.environ.get('QDRANT_URL', 'Not set')}")
    print("="*80)
    
    # Check connection first
    if not await check_connection():
        print("\nCannot proceed without database connection.")
        return
    
    # Verify indexed content
    await verify_indexed_content()

if __name__ == "__main__":
    asyncio.run(main()) 