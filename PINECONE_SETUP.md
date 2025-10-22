# 📌 Pinecone Setup Guide

This guide shows you how to index your documents into Pinecone and use them with the Trustworthy RAG system.

## ✅ Your Current Setup

Based on your Pinecone index configuration:
- **Index Name**: `seniorseminar`
- **Embedding Model**: `text-embedding-3-large` (OpenAI)
- **Dimension**: 1024
- **Metric**: cosine

## 🚀 Quick Start - Index Your Documents

### Step 1: Set Environment Variables

```bash
export OPENAI_API_KEY='your-openai-key-here'
export PINECONE_API_KEY='your-pinecone-key-here'
```

Or add them to your `.env` file:
```bash
OPENAI_API_KEY=your-openai-key-here
PINECONE_API_KEY=your-pinecone-key-here
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

This includes:
- `pinecone-client==3.0.3`
- `openai>=1.35.0`
- `langchain-openai==0.1.23`

### Step 3: Index Documents

**Option A: Standard Document Set (12 documents)**
```bash
cd scripts
python index_to_pinecone.py
```

**Option B: Expanded Document Set (15 documents)**
```bash
cd scripts
python index_to_pinecone.py --expanded
```

The script will:
1. ✅ Load documents from JSON
2. ✅ Generate embeddings using `text-embedding-3-large`
3. ✅ Upsert vectors to Pinecone index `seniorseminar`
4. ✅ Show progress and statistics

**Expected Output:**
```
📄 Using STANDARD document set (12 documents)
🎯 Target Index: seniorseminar
📦 Namespace: default
============================================================
✅ API keys found

🚀 Starting to index 12 documents...
Indexing documents: 100%|████████████| 12/12 [00:03<00:00,  3.2it/s]
✅ Indexing complete!
   Total: 12/12 documents
   Duration: 3.75s
   Speed: 3.20 docs/sec

============================================================
✅ INDEXING COMPLETE!
============================================================
📊 Statistics:
   Total documents: 12
   Successfully indexed: 12
   Failed: 0
   Duration: 3.75s
   Speed: 3.2 docs/sec

🎉 Your documents are now searchable in Pinecone!
```

### Step 4: Verify in Pinecone Console

1. Go to https://app.pinecone.io
2. Select your `seniorseminar` index
3. Check the vector count (should show 12 or 15)
4. You can query directly in the console to test

## 📚 Document Sets

### Standard Set (12 documents)
- Financial reports (Q1, Q2)
- HR documents (benefits, onboarding, performance reviews)
- Healthcare compliance (HIPAA, patient privacy, equipment)
- Public information (company info, CSR, tech stack)
- Legal contracts

### Expanded Set (15 documents)
Everything in standard set PLUS:
- Product roadmap
- Information security policy
- Remote work policy

Each document is ~2-3x larger with more detailed content.

## 🔧 Using Pinecone with the RAG System

### CLI Mode

The system automatically uses Pinecone if the API key is set:

```bash
cd src
python app.py
```

The retriever will:
1. ✅ Connect to `seniorseminar` index
2. ✅ Use hybrid search (Pinecone semantic + TF-IDF keyword)
3. ✅ Apply validation and PII masking
4. ✅ Generate secure responses

### API Mode

```bash
cd src
python -m uvicorn api:app --reload
```

Then query via API:
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are our Q2 financial results?",
    "user": {"username": "analyst", "role": "analyst"},
    "k": 5
  }'
```

### Python Code

```python
from retriever import HybridRetriever
import json

# Load documents
with open('../data/expanded_docs.json') as f:
    documents = json.load(f)

# Initialize retriever with Pinecone
retriever = HybridRetriever(
    documents=documents,
    use_pinecone=True,  # Will use Pinecone
    pinecone_index_name='seniorseminar',
    pinecone_namespace='default'
)

# Query
results = retriever.retrieve("What are the Q2 financial highlights?", k=5)

for doc in results:
    print(f"{doc['title']}: {doc['relevance_score']:.3f}")
```

## 🔍 Advanced Usage

### Using Different Namespaces

You can organize documents by namespace:

```bash
# Index to production namespace
python index_to_pinecone.py --namespace production

# Index to development namespace
python index_to_pinecone.py --namespace development
```

Then specify namespace in code:
```python
retriever = HybridRetriever(
    documents=documents,
    pinecone_namespace='production'
)
```

### Re-indexing Documents

To update documents in Pinecone:

1. **Delete existing vectors** (optional, script overwrites):
```python
from utils.pinecone_manager import PineconeIndexManager

manager = PineconeIndexManager(index_name='seniorseminar')
manager.delete_namespace('default')  # Clears namespace
```

2. **Re-run indexing script**:
```bash
python index_to_pinecone.py --expanded
```

### Checking Index Stats

```python
from utils.pinecone_manager import PineconeIndexManager

manager = PineconeIndexManager(index_name='seniorseminar')
stats = manager.get_index_stats()

print(f"Total vectors: {stats['total_vectors']}")
print(f"Dimension: {stats['dimension']}")
print(f"Namespaces: {stats['namespaces']}")
```

### Querying Pinecone Directly

```python
from utils.pinecone_manager import PineconeIndexManager

manager = PineconeIndexManager(index_name='seniorseminar')

# Search for similar documents
results = manager.query_similar(
    query="Show me financial information",
    top_k=5,
    filter_dict={'domain': 'finance'}  # Optional metadata filter
)

for doc in results:
    print(f"{doc['title']}: score={doc['score']:.3f}")
```

## 📊 Performance

### Embedding Generation
- **Model**: text-embedding-3-large
- **Dimensions**: 1024
- **Speed**: ~3-5 docs/second
- **Cost**: $0.13 per 1M tokens

### Pinecone Query
- **Latency**: ~50-100ms per query
- **Accuracy**: High (cosine similarity)
- **Scale**: Millions of vectors supported

### Hybrid Search
- **Semantic (Pinecone)**: Understands meaning
- **Keyword (TF-IDF)**: Exact term matching
- **Combined**: Best of both worlds

## 🐛 Troubleshooting

### Error: "Index 'seniorseminar' does not exist"
**Solution**: Index must be created in Pinecone console first. The script doesn't create it automatically.

### Error: "PINECONE_API_KEY not set"
**Solution**: Export the environment variable or add to `.env` file.

### Error: "Rate limit exceeded"
**Solution**: Pinecone free tier has limits. Slow down indexing or upgrade plan.

### Error: "Dimension mismatch"
**Solution**: Ensure embeddings are 1024 dimensions (text-embedding-3-large).

### Slow Indexing
**Solution**: 
- Process in smaller batches
- Check internet connection
- Verify API rate limits

### Documents Not Found in Queries
**Solution**:
- Verify documents are indexed: Check Pinecone console
- Check namespace matches between indexing and querying
- Try increasing `k` parameter for more results

## 📖 Additional Resources

- **Pinecone Docs**: https://docs.pinecone.io
- **OpenAI Embeddings**: https://platform.openai.com/docs/guides/embeddings
- **Project README**: See main README.md for full system documentation
- **Architecture**: See ARCHITECTURE.md for technical details

## 💡 Tips

1. **Start Small**: Use standard set (12 docs) first to test
2. **Monitor Costs**: Track OpenAI API usage for embeddings
3. **Use Namespaces**: Organize by environment (dev/staging/prod)
4. **Test Locally**: Use FAISS fallback for development
5. **Cache Queries**: Enable Redis caching for better performance

## 🎯 Next Steps

After indexing:

1. ✅ Run CLI: `cd src && python app.py`
2. ✅ Try different user roles to test RBAC
3. ✅ Start API: `python -m uvicorn api:app --reload`
4. ✅ Test multi-agent queries with `use_agents: true`
5. ✅ Monitor metrics at `/metrics` endpoint

---

**Need Help?**
- Check logs: `tail -f logs/trustworthy_rag.log`
- Test Pinecone connection in console
- Verify API keys are active
- See main README for more examples

