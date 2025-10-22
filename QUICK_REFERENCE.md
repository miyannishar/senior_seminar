# 🚀 Quick Reference Card

## 📋 Essential Commands

### Setup & Installation
```bash
# One-time setup
./setup.sh

# Or manual
pip install -r requirements.txt
export OPENAI_API_KEY='your-key'
export PINECONE_API_KEY='your-key'
```

### Index Documents to Pinecone
```bash
# Standard set (12 docs)
make index-pinecone

# Expanded set (15 docs)
make index-pinecone-expanded

# Or directly
cd scripts && python index_to_pinecone.py --expanded
```

### Run the System
```bash
# CLI mode
make run

# API mode
make run-api

# Docker
docker-compose up -d
```

### Testing
```bash
# All tests
make test

# With coverage
make test-coverage

# Specific tests
pytest tests/test_validator.py -v
```

## 🔑 API Endpoints

### Base URL
`http://localhost:8000`

### Key Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/docs` | GET | Interactive API documentation |
| `/health` | GET | Health check |
| `/query` | POST | Standard RAG query |
| `/query/compliance` | POST | Compliance-aware query |
| `/metrics` | GET | Prometheus metrics |
| `/stats` | GET | System statistics |

### Example Query
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the Q2 financial highlights?",
    "user": {"username": "analyst", "role": "analyst"},
    "k": 5,
    "use_agents": false
  }'
```

## 👥 User Roles & Access

| Role | Access Domains | Use Case |
|------|----------------|----------|
| `admin` | finance, hr, health, legal, public | Full access |
| `analyst` | finance, hr, public | Business analysis |
| `manager` | hr, public | People management |
| `employee` | public | General staff |
| `guest` | public | External users |

## 📊 Document Domains

- **finance**: Financial reports, sales data
- **hr**: Employee benefits, policies, reviews
- **health**: HIPAA, patient data, medical equipment
- **legal**: Contracts, compliance
- **public**: Company info, technology, CSR

## 🔧 Configuration Files

| File | Purpose |
|------|---------|
| `.env` | API keys and environment variables |
| `data/sample_docs.json` | Standard document set (12 docs) |
| `data/expanded_docs.json` | Expanded set (15 docs) |
| `requirements.txt` | Python dependencies |
| `docker-compose.yml` | Docker services configuration |
| `pytest.ini` | Test configuration |

## 📁 Key Files

| File | Description |
|------|-------------|
| `src/api.py` | FastAPI REST API |
| `src/app.py` | CLI application |
| `src/retriever.py` | Hybrid retrieval (Pinecone/FAISS + TF-IDF) |
| `src/validator.py` | Validation, RBAC, PII masking |
| `src/generator.py` | LLM response generation |
| `src/agents.py` | Multi-agent orchestration |
| `src/utils/cache.py` | Caching layer |
| `src/utils/metrics.py` | Performance metrics |
| `src/utils/pinecone_manager.py` | Pinecone operations |
| `scripts/index_to_pinecone.py` | Document indexing script |

## 🔍 Common Tasks

### Query Documents
**CLI:**
```bash
cd src && python app.py
# Select role, enter query
```

**API:**
```bash
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{"query": "...", "user": {...}}'
```

### Multi-Agent Query
```json
{
  "query": "Analyze Q2 performance and identify compliance gaps",
  "user": {"username": "admin", "role": "admin"},
  "use_agents": true
}
```

### Check Index Stats
```python
from utils.pinecone_manager import PineconeIndexManager

manager = PineconeIndexManager(index_name='seniorseminar')
stats = manager.get_index_stats()
print(stats)
```

### Clear Cache
```python
from utils.cache import get_cache

cache = get_cache()
cache.clear()
```

### View Metrics
```bash
# Prometheus
open http://localhost:9090

# Grafana  
open http://localhost:3000

# API metrics
curl http://localhost:8000/metrics
```

## 🛠️ Troubleshooting

### API Key Not Set
```bash
export OPENAI_API_KEY='sk-...'
export PINECONE_API_KEY='...'
```

### Port Already in Use
```bash
# Change port in .env or command
uvicorn api:app --port 8001
```

### Documents Not Found
```bash
# Re-index to Pinecone
make index-pinecone-expanded
```

### Cache Issues
```bash
# Restart Redis
docker-compose restart redis

# Or clear cache
redis-cli FLUSHALL
```

### Test Failures
```bash
# Skip integration tests
pytest -m unit

# Update environment
pip install -r requirements.txt
```

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| `README.md` | Complete user guide |
| `ARCHITECTURE.md` | Technical architecture |
| `QUICKSTART.md` | 5-minute quick start |
| `PINECONE_SETUP.md` | Pinecone indexing guide |
| `CHANGELOG.md` | Version history |

## 🔗 Useful URLs (when running)

| Service | URL | Credentials |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | - |
| Prometheus | http://localhost:9090 | - |
| Grafana | http://localhost:3000 | admin/admin |
| Redis | localhost:6379 | - |

## 💡 Pro Tips

1. **Use make help** to see all available commands
2. **Start with expanded docs** for better coverage
3. **Enable agents** for complex queries
4. **Monitor metrics** in production
5. **Use namespaces** in Pinecone for different environments
6. **Test with different roles** to verify RBAC
7. **Check logs** at `logs/trustworthy_rag.log`
8. **Export interaction logs** for analysis

## 🎯 Performance Benchmarks

| Metric | Value |
|--------|-------|
| Embedding generation | ~200ms per doc |
| Pinecone query | ~50-100ms |
| TF-IDF search | ~20ms |
| Validation | ~10ms |
| LLM generation | ~1-3s |
| **Total query time** | **~1.3-3.5s** |
| Cache hit speedup | **80%+ faster** |

## 🔐 Security Checklist

- [ ] API keys in .env (not committed)
- [ ] RBAC tested for all roles
- [ ] PII masking verified
- [ ] Audit logs enabled
- [ ] Compliance frameworks configured
- [ ] Docker non-root user
- [ ] Network policies set
- [ ] Rate limiting enabled (production)

---

**Need Help?**
- Run: `make help`
- Check: `QUICKSTART.md`
- Read: `PINECONE_SETUP.md`
- Logs: `tail -f logs/trustworthy_rag.log`

