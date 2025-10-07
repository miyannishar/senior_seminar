"""
Hybrid Retrieval Module
Combines semantic similarity search with keyword-based TF-IDF retrieval
for both contextual relevance and precision in document retrieval.
"""

from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
from typing import List, Dict, Any
import os


class HybridRetriever:
    """
    Hybrid retrieval system combining semantic search (via embeddings)
    and keyword-based search (via TF-IDF).
    """
    
    def __init__(self, documents: List[Dict[str, Any]]):
        """
        Initialize the hybrid retriever with a list of documents.
        
        Args:
            documents: List of document dictionaries with 'id', 'content', 'title', etc.
        """
        self.documents = documents
        
        # Check if OpenAI API key is set
        if not os.getenv("OPENAI_API_KEY"):
            print("⚠️  Warning: OPENAI_API_KEY not set. Semantic search will fail.")
            print("   Set it with: export OPENAI_API_KEY='your-key-here'")
        
        # Initialize embeddings and vector store
        self.embeddings = OpenAIEmbeddings()
        
        # Create FAISS vector store from documents
        texts = [d['content'] for d in documents]
        metadatas = [{'id': d['id'], 'title': d.get('title', ''), 'domain': d.get('domain', '')} 
                     for d in documents]
        
        self.vector_store = FAISS.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas
        )
        
        # Initialize keyword-based TF-IDF retriever
        self.keyword_index = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2)  # Include bigrams for better matching
        )
        self.keyword_matrix = self.keyword_index.fit_transform(texts)
        
        print(f"✅ HybridRetriever initialized with {len(documents)} documents")
    
    def retrieve(self, query: str, k: int = 5, semantic_weight: float = 0.7) -> List[Dict[str, Any]]:
        """
        Retrieve documents using hybrid approach (semantic + keyword).
        
        Args:
            query: The search query
            k: Number of documents to retrieve
            semantic_weight: Weight for semantic results (0-1), keyword weight is (1 - semantic_weight)
        
        Returns:
            List of retrieved document dictionaries
        """
        try:
            # Semantic retrieval using FAISS
            semantic_docs = self.vector_store.similarity_search(query, k=k)
            semantic_results = []
            
            for doc in semantic_docs:
                # Find original document by ID
                doc_id = doc.metadata.get('id', '')
                original_doc = next((d for d in self.documents if d['id'] == doc_id), None)
                if original_doc:
                    result = original_doc.copy()
                    result['retrieval_method'] = 'semantic'
                    result['relevance_score'] = semantic_weight
                    semantic_results.append(result)
        except Exception as e:
            print(f"⚠️  Semantic search failed: {e}")
            semantic_results = []
        
        # Keyword-based retrieval using TF-IDF
        keyword_vec = self.keyword_index.transform([query])
        keyword_scores = np.dot(keyword_vec, self.keyword_matrix.T).toarray().flatten()
        keyword_indices = keyword_scores.argsort()[-k:][::-1]
        
        keyword_results = []
        for idx in keyword_indices:
            if keyword_scores[idx] > 0:  # Only include if there's some relevance
                result = self.documents[idx].copy()
                result['retrieval_method'] = 'keyword'
                result['relevance_score'] = (1 - semantic_weight) * keyword_scores[idx]
                keyword_results.append(result)
        
        # Merge and deduplicate results
        merged = {}
        for doc in semantic_results + keyword_results:
            doc_id = doc['id']
            if doc_id not in merged:
                merged[doc_id] = doc
            else:
                # Keep the one with higher relevance score
                if doc['relevance_score'] > merged[doc_id]['relevance_score']:
                    merged[doc_id] = doc
        
        # Sort by relevance score and return top k
        final_results = sorted(merged.values(), key=lambda x: x['relevance_score'], reverse=True)[:k]
        
        print(f"📊 Retrieved {len(final_results)} documents for query: '{query[:50]}...'")
        return final_results
    
    def retrieve_by_domain(self, query: str, domain: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve documents filtered by a specific domain.
        
        Args:
            query: The search query
            domain: Domain filter (e.g., 'finance', 'hr', 'health')
            k: Number of documents to retrieve
        
        Returns:
            List of retrieved document dictionaries from the specified domain
        """
        results = self.retrieve(query, k=k*2)  # Retrieve more to account for filtering
        filtered = [doc for doc in results if doc.get('domain') == domain]
        return filtered[:k]

