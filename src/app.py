"""
Main Application Entry Point
Trustworthy RAG System - Enterprise AI with Privacy & Validation

This application demonstrates a production-ready RAG system with:
- Hybrid retrieval (semantic + keyword)
- Privacy filtering and PII masking
- Role-based access control
- Comprehensive logging and traceability
"""

import json
import os
import sys
from typing import Dict, Any, List
from dotenv import load_dotenv

from generator import SecureRAGGenerator, export_logs

# Load environment variables from .env file
load_dotenv()


def load_documents(filepath: str = "../data/sample_docs.json") -> List[Dict[str, Any]]:
    """
    Load documents from JSON file.
    
    Args:
        filepath: Path to documents JSON file
    
    Returns:
        List of document dictionaries
    """
    # Handle relative path from src directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(current_dir, filepath)
    
    try:
        with open(full_path, 'r') as f:
            documents = json.load(f)
        print(f"✅ Loaded {len(documents)} documents from {filepath}")
        return documents
    except FileNotFoundError:
        print(f"❌ Error: Could not find document file at {full_path}")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"❌ Error: Invalid JSON in {filepath}")
        sys.exit(1)


def print_banner():
    """Print application banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║        🛡️  TRUSTWORTHY RAG SYSTEM - ENTERPRISE AI               ║
║                                                                   ║
║        Secure • Private • Validated • Traceable                  ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_response(response: str, sources: List[Dict], metadata: Dict):
    """
    Pretty print the response with sources and metadata.
    
    Args:
        response: Generated response text
        sources: List of source documents
        metadata: Response metadata
    """
    print("\n" + "─" * 80)
    print("📄 RESPONSE:")
    print("─" * 80)
    print(response)
    print("\n" + "─" * 80)
    print("📚 SOURCES:")
    print("─" * 80)
    
    if sources:
        for i, source in enumerate(sources, 1):
            print(f"  {i}. {source.get('title', 'Untitled')} (ID: {source.get('id')}, Domain: {source.get('domain', 'N/A')})")
    else:
        print("  No sources available")
    
    print("\n" + "─" * 80)
    print("📊 METADATA:")
    print("─" * 80)
    for key, value in metadata.items():
        print(f"  {key}: {value}")
    print("─" * 80 + "\n")


def interactive_mode(rag_generator: SecureRAGGenerator):
    """
    Run the RAG system in interactive mode.
    
    Args:
        rag_generator: Initialized SecureRAGGenerator instance
    """
    print("\n🎮 Entering interactive mode...")
    
    # Ask user to select their role
    print("\n👤 Select your role:")
    print("  1. admin    - Full access to all domains")
    print("  2. analyst  - Access to finance, hr, public")
    print("  3. manager  - Access to hr, public")
    print("  4. employee - Access to public only")
    print("  5. guest    - Access to public only")
    
    role_map = {
        "1": "admin",
        "2": "analyst",
        "3": "manager",
        "4": "employee",
        "5": "guest"
    }
    
    while True:
        role_choice = input("\nEnter choice (1-5): ").strip()
        if role_choice in role_map:
            selected_role = role_map[role_choice]
            break
        else:
            print("❌ Invalid choice. Please enter 1-5.")
    
    # Get username
    username = input("Enter your username (or press Enter for 'demo_user'): ").strip()
    if not username:
        username = "demo_user"
    
    current_user = {
        "username": username,
        "role": selected_role
    }
    
    print(f"\n✅ Logged in as: {current_user['username']} (Role: {current_user['role']})")
    print("\nCommands:")
    print("  - Type your question to query the system")
    print("  - Type 'switch' to change user role")
    print("  - Type 'export' to export logs")
    print("  - Type 'exit' to quit\n")
    
    while True:
        try:
            query = input("💬 Query: ").strip()
            
            if not query:
                continue
            
            if query.lower() == 'exit':
                print("\n👋 Goodbye!")
                break
            
            if query.lower() == 'switch':
                print("\n👤 Select new role:")
                print("  1. admin    - Full access to all domains")
                print("  2. analyst  - Access to finance, hr, public")
                print("  3. manager  - Access to hr, public")
                print("  4. employee - Access to public only")
                print("  5. guest    - Access to public only")
                
                role_choice = input("\nEnter choice (1-5): ").strip()
                if role_choice in role_map:
                    current_user['role'] = role_map[role_choice]
                    print(f"✅ Switched to role: {current_user['role']}\n")
                else:
                    print("❌ Invalid choice\n")
                continue
            
            if query.lower() == 'export':
                export_logs()
                continue
            
            # Generate response
            response, sources, metadata = rag_generator.generate_secure_response(
                query=query,
                user=current_user,
                k=5
            )
            
            # Display results
            print_response(response, sources, metadata)
            
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}\n")


def demo_mode(rag_generator: SecureRAGGenerator):
    """
    Run predefined demo queries to showcase the system.
    
    Args:
        rag_generator: Initialized SecureRAGGenerator instance
    """
    print("\n🎬 Running demo mode with sample queries...\n")
    
    demo_queries = [
        {
            "user": {"username": "finance_analyst", "role": "analyst"},
            "query": "Summarize the Q2 financial report without showing confidential figures."
        },
        {
            "user": {"username": "hr_manager", "role": "manager"},
            "query": "What are the key employee benefits mentioned in the documents?"
        },
        {
            "user": {"username": "guest_user", "role": "guest"},
            "query": "What public information is available about the company?"
        },
        {
            "user": {"username": "admin_user", "role": "admin"},
            "query": "Show me all healthcare-related compliance requirements."
        }
    ]
    
    for i, demo in enumerate(demo_queries, 1):
        print(f"\n{'='*80}")
        print(f"DEMO QUERY {i}/{len(demo_queries)}")
        print(f"User: {demo['user']['username']} (Role: {demo['user']['role']})")
        print(f"Query: {demo['query']}")
        print('='*80)
        
        response, sources, metadata = rag_generator.generate_secure_response(
            query=demo['query'],
            user=demo['user'],
            k=5
        )
        
        print_response(response, sources, metadata)
        
        input("\nPress Enter to continue to next demo...")
    
    print("\n✅ Demo completed!")


def main():
    """Main application entry point."""
    print_banner()
    
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  WARNING: OPENAI_API_KEY environment variable is not set!")
        print("   The system will run in limited mode without actual LLM generation.")
        print("   To enable full functionality, set your API key:")
        print("   export OPENAI_API_KEY='your-openai-api-key-here'")
        print()
        
        response = input("Continue in limited mode? (y/n): ").strip().lower()
        if response != 'y':
            print("Exiting...")
            sys.exit(0)
    
    # Load documents
    print("\n📂 Loading documents...")
    documents = load_documents()
    
    # Initialize RAG system
    print("\n🔧 Initializing Trustworthy RAG system...")
    rag_generator = SecureRAGGenerator(
        documents=documents,
        model_name="gpt-3.5-turbo",  # Use gpt-4 for better results
        temperature=0.7
    )
    
    print("\n✅ System ready!")
    
    # Choose mode
    print("\nSelect mode:")
    print("  1. Interactive mode (ask your own questions)")
    print("  2. Demo mode (run predefined examples)")
    
    mode = input("\nEnter choice (1 or 2): ").strip()
    
    if mode == "1":
        interactive_mode(rag_generator)
    elif mode == "2":
        demo_mode(rag_generator)
    else:
        print("Invalid choice. Running interactive mode by default.")
        interactive_mode(rag_generator)
    
    # Export logs before exit
    print("\n📊 Exporting interaction logs...")
    export_logs()
    
    print("\n✅ All done! Logs saved to interaction_logs.json")


if __name__ == "__main__":
    main()

