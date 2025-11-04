"""
Hybrid Retrieval Module with Pinecone Support
Combines semantic similarity search with keyword-based TF-IDF retrieval
for both contextual relevance and precision in document retrieval.
Supports both FAISS (local) and Pinecone (production) vector stores.
"""

import os
from typing import List, Dict, Any, Optional
import numpy as np

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from sklearn.feature_extraction.text import TfidfVectorizer

from utils.logger import setup_logger
from utils.exceptions import RetrievalException

logger = setup_logger(__name__)

# Try to import Pinecone (optional dependency)
try:
    from pinecone import Pinecone, ServerlessSpec
    PINECONE_AVAILABLE = True
except ImportError:
    PINECONE_AVAILABLE = False
    logger.warning("⚠️  Pinecone not installed. Using FAISS only. Install with: pip install pinecone-client")


class HybridRetriever:
    """
    Production-ready hybrid retrieval system combining:
    - Semantic search via embeddings (Pinecone or FAISS)
    - Keyword search via TF-IDF
    """
    
    def __init__(
        self, 
        documents: List[Dict[str, Any]],
        use_pinecone: bool = True,
        pinecone_index_name: str = "seniorseminar",
        pinecone_namespace: str = "default"
    ):
        """
        Initialize the hybrid retriever with documents.
        
        Args:
            documents: List of document dictionaries
            use_pinecone: Whether to use Pinecone (if available)
            pinecone_index_name: Name of Pinecone index
            pinecone_namespace: Namespace within Pinecone index
        """
        self.documents = documents
        self.pinecone_index_name = pinecone_index_name
        self.pinecone_namespace = pinecone_namespace
        
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            logger.warning("⚠️  OPENAI_API_KEY not set. Semantic search will fail.")
            logger.warning("   Set it with: export OPENAI_API_KEY='your-key-here'")
        
        # Initialize embeddings with text-embedding-3-large model (1024 dimensions)
        # This matches the Pinecone index configuration
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-large",
            dimensions=1024
        )
        
        # Initialize vector store (Pinecone or FAISS)
        self.use_pinecone = use_pinecone and PINECONE_AVAILABLE and os.getenv("PINECONE_API_KEY")
        
        if self.use_pinecone:
            logger.info("🚀 Initializing Pinecone vector store...")
            self.vector_store = self._init_pinecone()
        else:
            if use_pinecone and not PINECONE_AVAILABLE:
                logger.warning("⚠️  Pinecone requested but not available. Falling back to FAISS.")
            elif use_pinecone and not os.getenv("PINECONE_API_KEY"):
                logger.warning("⚠️  PINECONE_API_KEY not set. Falling back to FAISS.")
            
            logger.info("📦 Initializing FAISS vector store...")
            self.vector_store = self._init_faiss()
        
        # Initialize keyword-based TF-IDF retriever
        self.keyword_index = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2),  # Include bigrams for better matching
            min_df=1,
            max_df=0.95
        )
        
        texts = [d['content'] for d in documents]
        self.keyword_matrix = self.keyword_index.fit_transform(texts)
        
        logger.info(f"✅ HybridRetriever initialized with {len(documents)} documents")
        logger.info(f"   Vector Store: {'Pinecone' if self.use_pinecone else 'FAISS'}")
    
    def _init_faiss(self):
        """Initialize FAISS vector store."""
        texts = [d['content'] for d in self.documents]
        metadatas = [
            {
                'id': d['id'], 
                'title': d.get('title', ''), 
                'domain': d.get('domain', ''),
                'doc_index': i  # Store original index for retrieval
            } 
            for i, d in enumerate(self.documents)
        ]
        
        return FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas
        )
    
    def _init_pinecone(self):
        """Initialize Pinecone vector store."""
        try:
            # Initialize Pinecone client
            pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
            
            # Check if index exists, create if not
            existing_indexes = [idx.name for idx in pc.list_indexes()]
            
            if self.pinecone_index_name not in existing_indexes:
                logger.info(f"📝 Creating new Pinecone index: {self.pinecone_index_name}")
                # Use 1024 dimensions for text-embedding-3-large model
                embedding_dimension = self.embeddings.dimensions if hasattr(self.embeddings, 'dimensions') else 1024
                pc.create_index(
                    name=self.pinecone_index_name,
                    dimension=embedding_dimension,  # Match embedding model dimension
                    metric='cosine',
                    spec=ServerlessSpec(
                        cloud='aws',
                        region='us-east-1'
                    )
                )
            
            # Get index
            index = pc.Index(self.pinecone_index_name)
            
            # Upsert documents
            logger.info("📤 Upserting documents to Pinecone...")
            batch_size = 100
            
            for i in range(0, len(self.documents), batch_size):
                batch = self.documents[i:i+batch_size]
                
                # Generate embeddings
                texts = [doc['content'] for doc in batch]
                embeddings = self.embeddings.embed_documents(texts)
                
                # Prepare vectors for upsert
                vectors = []
                for j, (doc, embedding) in enumerate(zip(batch, embeddings)):
                    doc_id = f"{doc['id']}_{self.pinecone_namespace}"
                    vectors.append({
                        'id': doc_id,
                        'values': embedding,
                        'metadata': {
                            'id': doc['id'],
                            'title': doc.get('title', ''),
                            'domain': doc.get('domain', ''),
                            'content_preview': doc['content'][:500],
                            'doc_index': i + j
                        }
                    })
                
                # Upsert to Pinecone
                index.upsert(vectors=vectors, namespace=self.pinecone_namespace)
            
            logger.info(f"✅ Pinecone index '{self.pinecone_index_name}' ready with {len(self.documents)} documents")
            
            return index
            
        except Exception as e:
            logger.error(f"❌ Pinecone initialization failed: {e}")
            logger.info("   Falling back to FAISS...")
            self.use_pinecone = False
            return self._init_faiss()
    
    def _semantic_search_faiss(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Perform semantic search using FAISS."""
        try:
            docs = self.vector_store.similarity_search(query, k=k)
            results = []
            
            for doc in docs:
                doc_id = doc.metadata.get('id', '')
                # Find original document
                original_doc = next((d for d in self.documents if d['id'] == doc_id), None)
                if original_doc:
                    result = original_doc.copy()
                    result['retrieval_method'] = 'semantic-faiss'
                    results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"⚠️  FAISS semantic search failed: {e}")
            return []
    
    def _semantic_search_pinecone(self, query: str, k: int) -> List[Dict[str, Any]]:
        """Perform semantic search using Pinecone."""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Query Pinecone
            results = self.vector_store.query(
                vector=query_embedding,
                top_k=k,
                namespace=self.pinecone_namespace,
                include_metadata=True
            )
            
            # Convert to document format
            docs = []
            for match in results.matches:
                doc_index = match.metadata.get('doc_index')
                # Convert to int if it's a float (Pinecone may return floats)
                if doc_index is not None:
                    try:
                        doc_index = int(doc_index)
                        if 0 <= doc_index < len(self.documents):
                            doc = self.documents[doc_index].copy()
                            doc['retrieval_method'] = 'semantic-pinecone'
                            doc['relevance_score'] = match.score
                            docs.append(doc)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"⚠️  Invalid doc_index {doc_index}: {e}")
                        continue
            
            return docs
            
        except Exception as e:
            logger.error(f"⚠️  Pinecone semantic search failed: {e}")
            return []
    
    def retrieve(
        self, 
        query: str, 
        k: int = 5, 
        semantic_weight: float = 0.7,
        keyword_weight: float = 0.3
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents using hybrid approach (semantic + keyword).
        
        Args:
            query: The search query
            k: Number of documents to retrieve
            semantic_weight: Weight for semantic results (0-1)
            keyword_weight: Weight for keyword results (0-1)
        
        Returns:
            List of retrieved document dictionaries
        """
        # Normalize weights
        total_weight = semantic_weight + keyword_weight
        semantic_weight = semantic_weight / total_weight
        keyword_weight = keyword_weight / total_weight
        
        # Semantic retrieval
        if self.use_pinecone:
            semantic_results = self._semantic_search_pinecone(query, k=k)
        else:
            semantic_results = self._semantic_search_faiss(query, k=k)
        
        # Add scores for semantic results
        for doc in semantic_results:
            if 'relevance_score' not in doc:
                doc['relevance_score'] = semantic_weight
            else:
                doc['relevance_score'] *= semantic_weight
        
        # Keyword-based retrieval using TF-IDF
        keyword_vec = self.keyword_index.transform([query])
        keyword_scores = np.dot(keyword_vec, self.keyword_matrix.T).toarray().flatten()
        keyword_indices = keyword_scores.argsort()[-k:][::-1]
        
        keyword_results = []
        for idx in keyword_indices:
            if keyword_scores[idx] > 0:  # Only include if there's some relevance
                result = self.documents[idx].copy()
                result['retrieval_method'] = 'keyword-tfidf'
                result['relevance_score'] = keyword_weight * float(keyword_scores[idx])
                keyword_results.append(result)
        
        # Merge and deduplicate results
        merged = {}
        for doc in semantic_results + keyword_results:
            doc_id = doc['id']
            if doc_id not in merged:
                merged[doc_id] = doc
            else:
                # Combine scores if document appears in both
                merged[doc_id]['relevance_score'] += doc['relevance_score']
                merged[doc_id]['retrieval_method'] = 'hybrid'
        
        # Sort by relevance score and return top k
        final_results = sorted(
            merged.values(), 
            key=lambda x: x.get('relevance_score', 0), 
            reverse=True
        )[:k]
        
        logger.info(f"📊 Retrieved {len(final_results)} documents for query: '{query[:50]}...'")
        logger.info(f"   Semantic: {len(semantic_results)}, Keyword: {len(keyword_results)}, Final: {len(final_results)}")
        
        return final_results
    
    def retrieve_by_domain(
        self, 
        query: str, 
        domain: str, 
        k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Retrieve documents filtered by a specific domain.
        
        Args:
            query: The search query
            domain: Domain filter (e.g., 'finance', 'hr', 'health')
            k: Number of documents to retrieve
        
        Returns:
            List of retrieved document dictionaries from the specified domain
        """
        # Retrieve more to account for filtering
        results = self.retrieve(query, k=k*3)
        filtered = [doc for doc in results if doc.get('domain') == domain]
        return filtered[:k]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retriever statistics."""
        return {
            'total_documents': len(self.documents),
            'vector_store': 'Pinecone' if self.use_pinecone else 'FAISS',
            'pinecone_index': self.pinecone_index_name if self.use_pinecone else None,
            'domains': list(set(doc.get('domain', 'unknown') for doc in self.documents))
        }
