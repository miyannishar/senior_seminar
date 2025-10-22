# 🚀 Quick Start Guide

Get up and running with Trustworthy RAG in 5 minutes!

## Prerequisites

- Python 3.9+
- OpenAI API key
- (Optional) Pinecone API key
- (Optional) Docker & Docker Compose

## Method 1: Automated Setup (Recommended)

```bash
# 1. Run the setup script
./setup.sh

# 2. Activate virtual environment
source venv/bin/activate

# 3. Run the application
make run
```

## Method 2: Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create .env file
cat > .env << EOF
OPENAI_API_KEY=your-openai-key-here
EOF

# 3. Run the CLI
cd src && python app.py
```

## Method 3: Docker (Production)

```bash
# 1. Create .env file with your API keys
cat > .env << EOF
OPENAI_API_KEY=your-key
PINECONE_API_KEY=your-key  # optional
EOF

# 2. Start all services
docker-compose up -d

# 3. Access the API
open http://localhost:8000/docs
```

## Your First Query

### CLI Mode

```bash
cd src && python app.py

# Select role: 2 (analyst)
# Enter query: "What are the Q2 financial highlights?"
```

### API Mode

```bash
# Start API server
make run-api

# Make a query
curl -X POST "http://localhost:8000/query" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are the Q2 financial highlights?",
    "user": {"username": "analyst", "role": "analyst"},
    "k": 5
  }'
```

### Python Code

```python
from generator import SecureRAGGenerator
import json

# Load documents
with open('data/sample_docs.json') as f:
    documents = json.load(f)

# Initialize RAG
rag = SecureRAGGenerator(documents)

# Query
response, sources, metadata = rag.generate_secure_response(
    query="What are the Q2 financial highlights?",
    user={"username": "analyst", "role": "analyst"},
    k=5
)

print(response)
```

## Test Different User Roles

The system has 5 roles with different access levels:

1. **admin** - Full access to all domains
2. **analyst** - Access to finance, hr, public
3. **manager** - Access to hr, public  
4. **employee** - Access to public only
5. **guest** - Access to public only

Try the same query with different roles to see access control in action!

## Next Steps

- 📖 Read the [full README](README.md) for detailed features
- 🏗️ Check [ARCHITECTURE.md](ARCHITECTURE.md) for technical details
- 🧪 Run tests: `make test`
- 📊 View metrics: http://localhost:9090 (Prometheus)
- 📈 View dashboards: http://localhost:3000 (Grafana)

## Common Commands

```bash
make help           # Show all available commands
make test           # Run tests
make run            # Run CLI application
make run-api        # Run API server
make docker-up      # Start Docker services
make docker-down    # Stop Docker services
make clean          # Clean generated files
```

## Troubleshooting

**Issue**: "OPENAI_API_KEY not set"  
**Solution**: Create `.env` file with your API key

**Issue**: "Module not found"  
**Solution**: Run `pip install -r requirements.txt`

**Issue**: "Tests failing"  
**Solution**: Ensure API keys are set, or skip integration tests with `pytest -m unit`

**Issue**: "Docker compose fails"  
**Solution**: Ensure ports 8000, 6379, 9090, 3000 are not in use

## Getting Help

- Check the [README](README.md)
- View API docs: http://localhost:8000/docs
- Review [ARCHITECTURE.md](ARCHITECTURE.md)
- Check logs: `tail -f logs/trustworthy_rag.log`

## What's Next?

1. **Explore Features**: Try multi-agent queries, compliance filtering
2. **Customize**: Add your own documents to `data/`
3. **Deploy**: Use Docker Compose for production deployment
4. **Monitor**: Set up Prometheus + Grafana for observability

Happy querying! 🎉

