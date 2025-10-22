"""
Pinecone Index Management Utilities
Handles document indexing, updates, and management for Pinecone vector store.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional
from tqdm import tqdm
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from langchain_openai import OpenAIEmbeddings
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Try to import Pinecone
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.error("Pinecone not installed. Install with: pip install pinecone-client")


class PineconeIndexManager:
    """
    Manager for Pinecone index operations.
    """
    
    def __init__(
        self,
        index_name: str = "seniorseminar",
        namespace: str = "default",
        dimension: int = 1024,
        metric: str = "cosine"
    ):
        """
        Initialize Pinecone index manager.
        
        Args:
            index_name: Name of the Pinecone index
            namespace: Namespace within the index
            dimension: Vector dimension (1024 for text-embedding-3-large)
            metric: Distance metric (cosine, euclidean, dotproduct)
        """
        if not PINECONE_AVAILABLE:
            raise ImportError("Pinecone not available")
        
        api_key = os.getenv("PINECONE_API_KEY")
        if not api_key:
            raise ValueError("PINECONE_API_KEY environment variable not set")
        
        self.index_name = index_name
        self.namespace = namespace
        self.dimension = dimension
        self.metric = metric
        
        # Initialize Pinecone client
        self.pc = Pinecone(api_key=api_key)
        
        # Initialize OpenAI embeddings with text-embedding-3-large model
        # and dimension 1024 to match your index
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            dimensions=1024  # Match your Pinecone index dimension
        )
        
        # Get or create index
        self.index = self._get_or_create_index()
        
        logger.info(f"✅ PineconeIndexManager initialized for index '{index_name}'")
    
    def _get_or_create_index(self):
        """Get existing index or create if it doesn't exist."""
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]
        
        if self.index_name not in existing_indexes:
            logger.warning(f"⚠️  Index '{self.index_name}' not found in Pinecone")
            logger.info("Please create the index in Pinecone console first")
            raise ValueError(f"Index '{self.index_name}' does not exist")
        
        logger.info(f"✅ Connected to existing index '{self.index_name}'")
        return self.pc.Index(self.index_name)
    
    def index_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100,
        show_progress: bool = True
    ) -> Dict[str, Any]:
        """
        Index documents into Pinecone.
        
        Args:
            documents: List of document dictionaries
            batch_size: Number of documents to process at once
            show_progress: Whether to show progress bar
        
        Returns:
            Dictionary with indexing statistics
        """
        logger.info(f"🚀 Starting to index {len(documents)} documents...")
        
        start_time = time.time()
        total_indexed = 0
        failed = 0
        
        # Process in batches
        iterator = range(0, len(documents), batch_size)
        if show_progress:
            iterator = tqdm(iterator, desc="Indexing documents")
        
        for i in iterator:
            batch = documents[i:i+batch_size]
            
            try:
                # Prepare texts and metadata
                texts = [doc['content'] for doc in batch]
                
                # Generate embeddings
                embeddings = self.embeddings.embed_documents(texts)
                
                # Prepare vectors for upsert
                vectors = []
                for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                    doc_id = f"{doc['id']}_{self.namespace}"
                    
                    # Prepare metadata (Pinecone has metadata size limits)
                    metadata = {
                        'id': doc['id'],
                        'title': doc.get('title', '')[:500],  # Limit size
                        'domain': doc.get('domain', 'unknown'),
                        'classification': doc.get('classification', 'internal'),
                        'author': doc.get('author', '')[:200],
                        'date': doc.get('date', ''),
                        'content_preview': doc['content'][:1000],  # First 1000 chars
                        'content_length': len(doc['content'])
                    }
                    
                    vectors.append({
                        'id': doc_id,
                        'values': embedding,
                        'metadata': metadata
                    })
                
                # Upsert to Pinecone
                self.index.upsert(vectors=vectors, namespace=self.namespace)
                total_indexed += len(batch)
                
            except Exception as e:
                logger.error(f"❌ Failed to index batch {i//batch_size + 1}: {e}")
                failed += len(batch)
        
        duration = time.time() - start_time
        
        stats = {
            'total_documents': len(documents),
            'successfully_indexed': total_indexed,
            'failed': failed,
            'duration_seconds': round(duration, 2),
            'docs_per_second': round(total_indexed / duration, 2) if duration > 0 else 0
        }
        
        logger.info(f"✅ Indexing complete!")
        logger.info(f"   Total: {total_indexed}/{len(documents)} documents")
        logger.info(f"   Duration: {duration:.2f}s")
        logger.info(f"   Speed: {stats['docs_per_second']:.2f} docs/sec")
        
        return stats
    
    def query_similar(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Query for similar documents.
        
        Args:
            query: Query text
            top_k: Number of results to return
            filter_dict: Metadata filters
        
        Returns:
            List of matching documents with scores
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        # Query Pinecone
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=self.namespace,
            include_metadata=True,
            filter=filter_dict
        )
        
        # Format results
        documents = []
        for match in results.matches:
            doc = {
                'id': match.metadata.get('id'),
                'score': match.score,
                'title': match.metadata.get('title'),
                'domain': match.metadata.get('domain'),
                'content_preview': match.metadata.get('content_preview')
            }
            documents.append(doc)
        
        return documents
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the index."""
        stats = self.index.describe_index_stats()
        
        return {
            'total_vectors': stats.total_vector_count,
            'dimension': stats.dimension,
            'namespaces': dict(stats.namespaces) if hasattr(stats, 'namespaces') else {},
            'index_fullness': stats.index_fullness if hasattr(stats, 'index_fullness') else 0
        }
    
    def delete_namespace(self, namespace: Optional[str] = None):
        """Delete all vectors in a namespace."""
        ns = namespace or self.namespace
        self.index.delete(delete_all=True, namespace=ns)
        logger.info(f"🗑️  Deleted all vectors in namespace '{ns}'")
    
    def delete_by_ids(self, ids: List[str]):
        """Delete specific document IDs."""
        prefixed_ids = [f"{id}_{self.namespace}" for id in ids]
        self.index.delete(ids=prefixed_ids, namespace=self.namespace)
        logger.info(f"🗑️  Deleted {len(ids)} documents")
    
    def update_document(self, document: Dict[str, Any]):
        """Update a single document."""
        self.index_documents([document], show_progress=False)
        logger.info(f"✅ Updated document: {document['id']}")


def index_from_json(
    json_path: str,
    index_name: str = "seniorseminar",
    namespace: str = "default"
) -> Dict[str, Any]:
    """
    Index documents from a JSON file.
    
    Args:
        json_path: Path to JSON file containing documents
        index_name: Pinecone index name
        namespace: Namespace to use
    
    Returns:
        Indexing statistics
    """
    # Load documents
    with open(json_path, 'r') as f:
        documents = json.load(f)
    
    logger.info(f"📄 Loaded {len(documents)} documents from {json_path}")
    
    # Initialize manager and index
    manager = PineconeIndexManager(index_name=index_name, namespace=namespace)
    stats = manager.index_documents(documents)
    
    return stats


if __name__ == "__main__":
    import sys
    
    # Simple CLI for indexing
    if len(sys.argv) < 2:
        print("Usage: python pinecone_manager.py <json_file_path>")
        print("Example: python pinecone_manager.py ../data/sample_docs.json")
        sys.exit(1)
    
    json_path = sys.argv[1]
    
    print("🛡️  Trustworthy RAG - Pinecone Indexing")
    print("=" * 50)
    
    try:
        stats = index_from_json(json_path)
        
        print("\n✅ Indexing Complete!")
        print(f"   Documents indexed: {stats['successfully_indexed']}")
        print(f"   Failed: {stats['failed']}")
        print(f"   Duration: {stats['duration_seconds']}s")
        print(f"   Speed: {stats['docs_per_second']} docs/sec")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

