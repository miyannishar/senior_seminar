#!/usr/bin/env python3
"""
Script to index documents to Pinecone
Usage: python index_to_pinecone.py [--expanded]
"""

import sys
import os
import argparse
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from utils.pinecone_manager import index_from_json

def main():
    parser = argparse.ArgumentParser(
        description='Index documents to Pinecone seniorseminar index'
    )
    parser.add_argument(
        '--expanded',
        action='store_true',
        help='Use expanded document set (15 docs instead of 12)'
    )
    parser.add_argument(
        '--index-name',
        default='seniorseminar',
        help='Pinecone index name (default: seniorseminar)'
    )
    parser.add_argument(
        '--namespace',
        default='default',
        help='Namespace to use (default: default)'
    )
    
    args = parser.parse_args()
    
    # Determine which document set to use
    if args.expanded:
        json_path = '../data/expanded_docs.json'
        print("📄 Using EXPANDED document set (15 documents)")
    else:
        json_path = '../data/sample_docs.json'
        print("📄 Using STANDARD document set (12 documents)")
    
    # Resolve path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, json_path)
    
    print(f"🎯 Target Index: {args.index_name}")
    print(f"📦 Namespace: {args.namespace}")
    print("=" * 60)
    
    # Check environment variables
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY not set")
        print("   Run: export OPENAI_API_KEY='your-key'")
        sys.exit(1)
    
    if not os.getenv('PINECONE_API_KEY'):
        print("❌ Error: PINECONE_API_KEY not set")
        print("   Run: export PINECONE_API_KEY='your-key'")
        sys.exit(1)
    
    print("✅ API keys found")
    print("")
    
    try:
        # Index documents
        stats = index_from_json(
            json_path=json_path,
            index_name=args.index_name,
            namespace=args.namespace
        )
        
        print("")
        print("=" * 60)
        print("✅ INDEXING COMPLETE!")
        print("=" * 60)
        print(f"📊 Statistics:")
        print(f"   Total documents: {stats['total_documents']}")
        print(f"   Successfully indexed: {stats['successfully_indexed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Duration: {stats['duration_seconds']}s")
        print(f"   Speed: {stats['docs_per_second']} docs/sec")
        print("")
        print("🎉 Your documents are now searchable in Pinecone!")
        print("")
        print("Next steps:")
        print("  1. Run the RAG system: cd src && python app.py")
        print("  2. Or start API: cd src && python -m uvicorn api:app --reload")
        print("  3. Try a query to see it in action!")
        
    except Exception as e:
        print("")
        print("=" * 60)
        print("❌ ERROR OCCURRED")
        print("=" * 60)
        print(f"Error: {e}")
        print("")
        print("Troubleshooting:")
        print("  1. Verify your Pinecone index exists at https://app.pinecone.io")
        print("  2. Check API keys are correct")
        print("  3. Ensure index name matches (default: seniorseminar)")
        print("  4. Check your Pinecone quota/limits")
        sys.exit(1)


if __name__ == "__main__":
    main()

