#!/usr/bin/env python3
"""
Test script to verify retrieval is working correctly with raw queries.
"""

import asyncio
import os
import sys

# Add the code directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'code'))

from retrieval.retriever import VectorDBClient

SITE_NAME = "makekismet"

async def test_direct_retrieval():
    """Test retrieval with exact FAQ questions."""
    
    print("Testing Direct Retrieval")
    print("="*80)
    
    # Initialize the vector DB client
    client = VectorDBClient()
    
    # Test with exact FAQ questions
    test_queries = [
        "How do I make sure AI can find my hotel?",
        "How does Kismet increase direct bookings?",
        "Does Kismet replace my booking engine?",
    ]
    
    for query in test_queries:
        print(f"\nTesting query: '{query}'")
        print("-" * 40)
        
        try:
            # Test search with the exact query
            results = await client.search(
                query=query,
                site=SITE_NAME,
                num_results=5
            )
            
            if results:
                print(f"✅ Found {len(results)} results")
                for i, result in enumerate(results[:3], 1):
                    if len(result) >= 1:
                        print(f"  {i}. URL: {result[0]}")
                        if len(result) >= 3:
                            print(f"     Name: {result[2]}")
            else:
                print("❌ NO RESULTS FOUND")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

async def test_keyword_retrieval():
    """Test retrieval with keywords."""
    
    print("\n\n" + "="*80)
    print("Testing Keyword Retrieval")
    print("="*80)
    
    client = VectorDBClient()
    
    # Test with keywords that should match
    keyword_tests = [
        "AI discovery SEO hotels",
        "increase direct bookings",
        "booking engine replacement",
        "hotel AI visibility",
    ]
    
    for keywords in keyword_tests:
        print(f"\nTesting keywords: '{keywords}'")
        print("-" * 40)
        
        try:
            results = await client.search(
                query=keywords,
                site=SITE_NAME,
                num_results=3
            )
            
            if results:
                print(f"✅ Found {len(results)} results")
                for i, result in enumerate(results[:2], 1):
                    if len(result) >= 1:
                        print(f"  {i}. URL: {result[0]}")
            else:
                print("❌ NO RESULTS FOUND")
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")

async def main():
    """Main test function."""
    print(f"Direct Retrieval Test Tool")
    print(f"Site: {SITE_NAME}")
    print(f"Database: {os.environ.get('QDRANT_URL', 'Not set')}")
    print("="*80)
    
    await test_direct_retrieval()
    await test_keyword_retrieval()

if __name__ == "__main__":
    asyncio.run(main()) 