# 🏗️ System Architecture - Trustworthy RAG

## Overview

This document provides a detailed technical overview of the Trustworthy RAG system architecture, including component interactions, data flows, and security considerations.

---

## Component Breakdown

### 1. Hybrid Retriever (`retriever.py`)

**Purpose**: Retrieve relevant documents using a combination of semantic and keyword-based search.

**Key Components**:
- **Semantic Search**: Uses OpenAI embeddings + FAISS vector store
  - Generates 1536-dimensional vectors for documents
  - Performs cosine similarity search
  - Handles paraphrased and abstract queries

- **Keyword Search**: Uses TF-IDF vectorization
  - Extracts important terms with inverse document frequency weighting
  - Supports exact term matching
  - Includes bigrams for phrase matching

**Process Flow**:
```
Query → [Embed] → Semantic Search (top-k)
      → [Vectorize] → Keyword Search (top-k)
      → Merge & Deduplicate → Ranked Results
```

**Key Methods**:
- `retrieve(query, k)`: Returns top-k documents using hybrid approach
- `retrieve_by_domain(query, domain, k)`: Filtered retrieval by domain

---

### 2. Validator (`validator.py`)

**Purpose**: Apply multi-layer validation to ensure privacy, security, and compliance.

**Validation Layers**:

1. **Role-Based Access Control (RBAC)**
   ```
   User Role → Check ROLE_ACCESS mapping → Allow/Deny domain
   ```
   
2. **Sensitive Term Detection**
   - Scans for predefined sensitive keywords
   - Flags documents containing: SSN, Salary, Confidential, etc.

3. **PII Masking**
   - Regex-based pattern matching
   - Masks: SSN, Credit Cards, Emails, Phone Numbers, Account IDs
   - Example: `123-45-6789` → `[MASKED-SSN]`

4. **Compliance Framework Validation**
   - HIPAA: Restricts PHI access, requires encryption
   - GDPR: Data minimization, consent requirements
   - SOX: Financial data audit trails

**Process Flow**:
```
Document → RBAC Check → Sensitive Term Scan → PII Masking → Validated Document
                ↓
          Access Denied (if failed)
```

**Key Functions**:
- `validation_filter(doc, user_role)`: Main validation pipeline
- `mask_sensitive_data(text)`: PII masking
- `batch_validate(documents, user_role)`: Bulk validation

**ComplianceValidator Class**:
- Framework-specific rule enforcement
- Extensible for custom compliance policies

---

### 3. Generator (`generator.py`)

**Purpose**: Generate secure, contextual responses using validated documents and LLM.

**Key Components**:

**SecureRAGGenerator Class**:
- Orchestrates retrieval → validation → generation pipeline
- Integrates with OpenAI's GPT models
- Maintains interaction logs

**Generation Pipeline**:
```
1. Query received
   ↓
2. Retrieve documents (HybridRetriever)
   ↓
3. Validate documents (batch_validate)
   ↓
4. Build context from validated docs
   ↓
5. Construct secure prompt
   ↓
6. LLM generates response
   ↓
7. Extract sources
   ↓
8. Log interaction
   ↓
9. Return response + sources + metadata
```

**Prompt Engineering**:
- System prompt enforces: context-only answers, no fabrication, source citation
- User prompt includes: validated context + user query
- Temperature control for consistency vs creativity balance

**Logging Decorator** (`@log_interaction`):
- Captures: user, query, timestamp, response, sources, duration
- Enables audit trails and compliance reporting
- Stores logs in-memory (production: external logging service)

**Key Methods**:
- `generate_secure_response(query, user, k)`: Main generation pipeline
- `generate_with_compliance(query, user, framework, k)`: Compliance-aware generation

---

### 4. Application (`app.py`)

**Purpose**: Main entry point providing interactive and demo modes.

**Features**:
- Document loading from JSON
- User role switching
- Interactive Q&A mode
- Automated demo mode with predefined queries
- Log export functionality

**User Flow**:
```
Start → Load Documents → Initialize RAG
      → Choose Mode (Interactive/Demo)
      → Execute Queries
      → View Results (Response + Sources + Metadata)
      → Export Logs
      → Exit
```

---

## Data Flow Diagram

```
┌──────────────┐
│ User Query   │
└──────┬───────┘
       │
       ▼
┌─────────────────────────────────────────────────┐
│           HybridRetriever                       │
│  ┌─────────────────┐  ┌────────────────────┐   │
│  │ Semantic Search │  │  Keyword Search    │   │
│  │   (Embeddings)  │  │     (TF-IDF)       │   │
│  └────────┬────────┘  └─────────┬──────────┘   │
│           │                     │               │
│           └──────────┬──────────┘               │
│                      │                          │
│            ┌─────────▼─────────┐                │
│            │ Merge & Dedupe    │                │
│            └─────────┬─────────┘                │
└──────────────────────┼──────────────────────────┘
                       │
           Retrieved Documents (5-10)
                       │
                       ▼
┌─────────────────────────────────────────────────┐
│              Validator                          │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Step 1: RBAC Check                      │  │
│  │  User Role vs Document Domain            │  │
│  └───────────────┬──────────────────────────┘  │
│                  │ (Pass/Deny)                 │
│                  ▼                              │
│  ┌──────────────────────────────────────────┐  │
│  │  Step 2: Sensitive Term Detection        │  │
│  └───────────────┬──────────────────────────┘  │
│                  │                              │
│                  ▼                              │
│  ┌──────────────────────────────────────────┐  │
│  │  Step 3: PII Masking                     │  │
│  │  (Regex-based substitution)              │  │
│  └───────────────┬──────────────────────────┘  │
│                  │                              │
└──────────────────┼──────────────────────────────┘
                   │
       Validated Documents (2-5)
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│           SecureRAGGenerator                    │
│                                                 │
│  ┌──────────────────────────────────────────┐  │
│  │  Assemble Context                        │  │
│  │  (Join validated doc contents)           │  │
│  └───────────────┬──────────────────────────┘  │
│                  │                              │
│                  ▼                              │
│  ┌──────────────────────────────────────────┐  │
│  │  Build Secure Prompt                     │  │
│  │  System: Instructions                    │  │
│  │  User: Context + Query                   │  │
│  └───────────────┬──────────────────────────┘  │
│                  │                              │
│                  ▼                              │
│  ┌──────────────────────────────────────────┐  │
│  │  LLM Generation (GPT-3.5/4)              │  │
│  └───────────────┬──────────────────────────┘  │
│                  │                              │
│                  ▼                              │
│  ┌──────────────────────────────────────────┐  │
│  │  Extract Sources & Metadata              │  │
│  └───────────────┬──────────────────────────┘  │
└──────────────────┼──────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────┐
│          Logging & Observability                │
│  • Timestamp                                    │
│  • User + Role                                  │
│  • Query                                        │
│  • Response Preview                             │
│  • Sources Used                                 │
│  • Retrieval/Validation Stats                   │
│  • Duration                                     │
│  • Status (success/error)                       │
└───────────────────┬─────────────────────────────┘
                    │
                    ▼
         ┌──────────────────────┐
         │  Response to User    │
         │  + Sources           │
         │  + Metadata          │
         └──────────────────────┘
```

---

## Security Architecture

### Defense in Depth Strategy

```
Layer 1: Authentication (Future)
         ↓
Layer 2: Authorization (RBAC) ✅
         ↓
Layer 3: Data Filtering (Domain-based) ✅
         ↓
Layer 4: PII Masking ✅
         ↓
Layer 5: Audit Logging ✅
         ↓
Layer 6: Compliance Validation ✅
```

### Current Security Features

1. **No Authentication** (Development mode)
   - Production: Integrate OAuth2, JWT, or SSO

2. **Role-Based Access Control** ✅
   - Enforced at validation layer
   - Granular domain-level permissions

3. **Data Masking** ✅
   - Automatic PII redaction
   - Configurable sensitivity levels

4. **Audit Trail** ✅
   - Complete interaction history
   - Exportable for compliance

5. **Secure Prompts** ✅
   - Prevents prompt injection
   - Instructs LLM to avoid fabrication

---

## Performance Considerations

### Latency Breakdown (Typical Query)

| Stage                    | Time     | Optimization Strategies                     |
|--------------------------|----------|---------------------------------------------|
| Embedding Generation     | ~200ms   | Batch queries, cache embeddings             |
| Vector Search (FAISS)    | ~50ms    | Use GPU-accelerated FAISS, optimize index   |
| Keyword Search (TF-IDF)  | ~20ms    | Pre-compute TF-IDF matrix                   |
| Validation               | ~10ms    | Optimize regex patterns, parallel validation|
| LLM Generation           | ~1-3s    | Use faster models (gpt-3.5-turbo), streaming|
| **Total**                | **~1.3-3.5s** | |

### Scalability

**Current (Single Machine)**:
- FAISS in-memory vector store
- Suitable for: <100K documents, <100 QPS

**Production (Distributed)**:
- **Pinecone**: Managed vector DB, scales to billions of vectors
- **Redis**: Cache for frequent queries
- **Load Balancer**: Distribute across multiple instances
- **Async Processing**: Queue-based architecture

---

## Deployment Architecture (Production)

```
┌─────────────────────────────────────────────────────────┐
│                     API Gateway                         │
│              (Authentication, Rate Limiting)             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  Load Balancer                          │
└───────┬──────────────────────┬──────────────────────────┘
        │                      │
        ▼                      ▼
┌──────────────┐      ┌──────────────┐       ┌──────────────┐
│ RAG Service  │      │ RAG Service  │  ...  │ RAG Service  │
│  Instance 1  │      │  Instance 2  │       │  Instance N  │
└──────┬───────┘      └──────┬───────┘       └──────┬───────┘
       │                     │                       │
       └─────────────────────┴───────────────────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
           ▼                 ▼                 ▼
    ┌───────────┐    ┌──────────────┐  ┌────────────┐
    │  Pinecone │    │  OpenAI API  │  │ PostgreSQL │
    │  (Vectors)│    │  (LLM/Embed) │  │   (Logs)   │
    └───────────┘    └──────────────┘  └────────────┘
```

---

## Technology Stack

### Core Dependencies

| Technology      | Version | Purpose                              |
|-----------------|---------|--------------------------------------|
| Python          | 3.9+    | Runtime                              |
| LangChain       | 0.1.0   | RAG orchestration                    |
| OpenAI API      | 1.6.1   | Embeddings & LLM                     |
| FAISS           | 1.7.4   | Vector similarity search             |
| scikit-learn    | 1.3.2   | TF-IDF, NLP utilities                |
| NumPy           | 1.24.3  | Numerical operations                 |

### Optional (Production)

- **Pinecone**: Production vector database
- **FastAPI**: REST API framework
- **PostgreSQL**: Persistent logging
- **Redis**: Caching layer
- **Docker/Kubernetes**: Containerization

---

## Code Quality & Best Practices

### Design Patterns Used

1. **Decorator Pattern**: `@log_interaction` for cross-cutting logging
2. **Strategy Pattern**: Compliance validators (HIPAA, GDPR, SOX)
3. **Builder Pattern**: Prompt construction in generator
4. **Repository Pattern**: Document loading/storage abstraction

### Testing Strategy (Future)

```python
# Unit Tests
test_retriever.py         # Hybrid retrieval accuracy
test_validator.py         # PII masking, RBAC logic
test_generator.py         # Response generation

# Integration Tests
test_end_to_end.py        # Full pipeline
test_compliance.py        # Compliance frameworks

# Performance Tests
test_latency.py           # Response time benchmarks
test_scalability.py       # Load testing
```

---

## Configuration Management

### Environment Variables

- `OPENAI_API_KEY`: Required for embeddings and generation
- `PINECONE_API_KEY`: Optional for production vector DB
- `MODEL_NAME`: LLM model selection (default: gpt-3.5-turbo)
- `TEMPERATURE`: Generation randomness (0.0-1.0)

### Configuration Files

- `data/sample_docs.json`: Document corpus
- `requirements.txt`: Python dependencies
- `.env`: Local environment variables (gitignored)

---

## Monitoring & Observability (Future)

### Key Metrics

1. **Performance Metrics**:
   - Query latency (p50, p95, p99)
   - Throughput (QPS)
   - Error rate

2. **Business Metrics**:
   - Queries per user
   - Average documents retrieved
   - Validation success rate

3. **Security Metrics**:
   - Access denials by role
   - PII detections
   - Compliance violations

### Logging

Current: In-memory logs → JSON export
Production: Structured logging to ELK, Datadog, or CloudWatch

---

## Future Enhancements

1. **Multi-Modal RAG**: Support PDFs, images, tables
2. **Streaming Responses**: Real-time LLM output
3. **Fine-Tuned Models**: Custom embeddings for domain-specific retrieval
4. **Feedback Loop**: User ratings to improve retrieval
5. **Multi-Agent Orchestration**: Complex reasoning with specialized agents
6. **Graph RAG**: Knowledge graph integration for relationship queries

---

**Document Version**: 1.0  
**Last Updated**: October 2025  
**Maintained By**: Research Team

