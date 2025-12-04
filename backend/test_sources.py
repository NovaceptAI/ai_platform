#!/usr/bin/env python3
"""
Test script for WebDock multi-source search functionality
"""
import sys
sys.path.insert(0, '/home/azureuser/ai_platform/backend')

from app.services.search_source_manager import SearchSourceManager

def test_sources():
    print("=" * 60)
    print("Testing WebDock Multi-Source Search")
    print("=" * 60)
    
    manager = SearchSourceManager()
    
    # List available sources
    print("\n1. Available Sources:")
    print("-" * 60)
    sources = manager.get_available_sources()
    for source in sources:
        status = "✓ Enabled" if source['enabled'] else "✗ Disabled"
        free = "🆓 FREE" if source['is_free'] else "💰 PAID"
        key = "🔑 Key Required" if source['requires_key'] else "🔓 No Key"
        print(f"{source['icon']} {source['display_name']:15} {status:12} {free:10} {key:15}")
        print(f"   {source['description']}")
        print(f"   Rate Limit: {source['rate_limit']}")
        print()
    
    # Test each source
    print("\n2. Testing Each Source:")
    print("-" * 60)
    test_results = manager.test_all_sources()
    for name, result in test_results.items():
        status = "✓" if result['available'] else "✗"
        print(f"{status} {name:15} - {result['message']}")
    
    # Test a search
    print("\n3. Testing Search (Python programming):")
    print("-" * 60)
    
    test_queries = [
        ('wikipedia', 'Python programming'),
        ('duckduckgo', 'machine learning'),
    ]
    
    for source, query in test_queries:
        print(f"\nSearching {source} for '{query}'...")
        try:
            results = manager.search(query, source=source, limit=3)
            if results['results']:
                print(f"✓ Found {len(results['results'])} results:")
                for i, r in enumerate(results['results'][:3], 1):
                    print(f"  {i}. {r['title'][:60]}...")
                    print(f"     {r['url']}")
            else:
                print(f"✗ No results found")
                if results['errors']:
                    print(f"     Errors: {results['errors']}")
        except Exception as e:
            print(f"✗ Error: {str(e)}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == '__main__':
    test_sources()
