#!/usr/bin/env python3
"""
Test script for new free search sources
"""
import sys
import os
sys.path.insert(0, '/home/azureuser/ai_platform/backend')

from app.services.sources import (
    RedditSource,
    GoogleBooksSource,
    StackExchangeSource,
    WikimediaCommonsSource,
    ProjectGutenbergSource
)

def test_source(source, query, source_name):
    print(f"\n{'='*60}")
    print(f"Testing {source_name}")
    print(f"{'='*60}")
    
    # Test availability
    available = source.is_available()
    print(f"Available: {available}")
    
    if not available:
        print(f"❌ {source_name} is not available")
        return False
    
    # Test search
    print(f"Searching for: '{query}'")
    try:
        results = source.search(query, limit=3)
        print(f"Found {len(results)} results\n")
        
        for i, result in enumerate(results, 1):
            print(f"{i}. {result.title}")
            print(f"   URL: {result.url}")
            print(f"   Snippet: {result.snippet[:100]}...")
            print(f"   Confidence: {result.confidence:.2f}")
            if result.metadata:
                print(f"   Metadata: {list(result.metadata.keys())}")
            print()
        
        return len(results) > 0
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    print("Testing new FREE search sources...")
    
    sources_to_test = [
        (RedditSource(), "Python programming", "Reddit"),
        (GoogleBooksSource(), "artificial intelligence", "Google Books"),
        (StackExchangeSource(), "Python async", "Stack Overflow"),
        (WikimediaCommonsSource(), "solar system", "Wikimedia Commons"),
        (ProjectGutenbergSource(), "Shakespeare", "Project Gutenberg"),
    ]
    
    results = []
    for source, query, name in sources_to_test:
        success = test_source(source, query, name)
        results.append((name, success))
    
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, success in results:
        status = "✅ Working" if success else "❌ Failed"
        print(f"{status}: {name}")

if __name__ == '__main__':
    main()
