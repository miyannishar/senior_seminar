# Trustworthy RAG Agentic System

A production-ready multi-agent RAG (Retrieval-Augmented Generation) system built with Google ADK (Agent Development Kit) that provides secure, role-based access to enterprise documents with deterministic PII masking and compliance validation.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [System Flow](#system-flow)
- [Directory Structure](#directory-structure)
- [Domain Agents](#domain-agents)
- [Security Features](#security-features)
- [Quick Start](#quick-start)
- [Usage Examples](#usage-examples)
- [Code Snippets](#code-snippets)
- [Configuration](#configuration)

## 🎯 Overview

This system implements a **trustworthy RAG pipeline** with the following key features:

- **Multi-Agent Architecture**: Base orchestrator routes queries to domain-specific sub-agents
- **Role-Based Access Control (RBAC)**: Deterministic access validation before data reaches LLM
- **PII Masking**: Automatic detection and masking of sensitive information
- **Hybrid Retrieval**: Combines semantic search (Pinecone) with keyword search (TF-IDF)
- **Domain Specialization**: Separate agents for Finance, HR, Health, and Legal domains
- **Compliance**: Built-in validation for HIPAA, GDPR, and other regulatory frameworks

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Base Orchestrator Agent                   │
│              (Routes queries to domain agents)               │
│                    Model: GPT-4o (Powerful)                 │
└───────────────────────┬─────────────────────────────────────┘
                        │
        ┌───────────────┼───────────────┐
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│  Financial   │ │     HR       │ │    Health    │ │     Law      │
│    Agent     │ │    Agent     │ │    Agent     │ │    Agent     │
│              │ │              │ │              │ │              │
│ GPT-4o-mini  │ │ GPT-4o-mini  │ │ GPT-4o-mini  │ │ GPT-4o-mini  │
│              │ │              │ │              │ │              │
│ RAG Tools:   │ │ RAG Tools:   │ │ RAG Tools:   │ │ RAG Tools:   │
│ - check_     │ │ - check_     │ │ - check_     │ │ - check_     │
│   access     │ │   access     │ │   access     │ │   access     │
│ - retrieve_  │ │ - retrieve_  │ │ - retrieve_  │ │ - retrieve_  │
│   and_       │ │   and_       │ │   and_       │ │   and_       │
│   validate   │ │   validate   │ │   validate   │ │   validate   │
│ - extract_   │ │ - extract_   │ │ - extract_   │ │ - extract_   │
│   info       │ │   info       │ │   info       │ │   info       │
└───────┬───────┘ └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
       │                 │                 │                 │
       └─────────────────┴─────────────────┴─────────────────┘
                         │
                         ▼
            ┌────────────────────────────┐
            │   Shared RAG Tools Layer   │
            │                            │
            │ - HybridRetriever          │
            │   ├─ Pinecone (semantic)   │
            │   └─ TF-IDF (keyword)      │
            │                            │
            │ - Validator                │
            │   ├─ Access Control        │
            │   ├─ PII Detection         │
            │   └─ Compliance Check      │
            └────────────────────────────┘
                         │
                         ▼
            ┌────────────────────────────┐
            │   Document Store           │
            │   (expanded_docs.json)     │
            │                            │
            │ Domains:                   │
            │ - finance                  │
            │ - hr                       │
            │ - health                   │
            │ - legal                    │
            │ - public                   │
            └────────────────────────────┘
```

## 🔄 System Flow

### 1. Query Routing Flow

```
User Query
    │
    ▼
Base Orchestrator Agent
    │
    ├─ Analyzes query domain
    │
    ├─ Identifies keywords (finance, HR, health, legal)
    │
    └─ Uses transfer_to_agent() to route to sub-agent
        │
        ├─► financial_agent
        ├─► hr_agent
        ├─► health_agent
        └─► law_agent
```

### 2. Domain Agent Processing Flow

```
Sub-Agent Receives Query
    │
    ▼
Step 1: Role Identification (REQUIRED)
    │
    ├─ Asks user: "What is your role in [department]?"
    │
    └─ Validates role against available roles
        │
        ▼
Step 2: Document Retrieval & Validation
    │
    ├─ Calls retrieve_and_validate()
    │   │
    │   ├─ Hybrid Retrieval (Pinecone + TF-IDF)
    │   │
    │   ├─ Domain Filtering
    │   │
    │   ├─ Access Control Check (DETERMINISTIC)
    │   │   └─ Maps department role → general role
    │   │   └─ Checks ROLE_ACCESS permissions
    │   │
    │   ├─ PII Masking (DETERMINISTIC)
    │   │   └─ Detects: SSN, AccountNumber, etc.
    │   │   └─ Masks based on role
    │   │
    │   └─ Returns ONLY validated, masked documents
    │
    ▼
Step 3: Information Extraction
    │
    ├─ Calls extract_info() with validated documents
    │
    └─ Builds context from masked documents
        │
        ▼
Step 4: Response Generation
    │
    ├─ LLM generates answer from validated context
    │
    ├─ Cites sources
    │
    └─ Returns to Base Agent → User
```

### 3. Security Flow (Deterministic Validation)

```
Document Retrieved
    │
    ▼
Access Check (BEFORE LLM sees data)
    │
    ├─ Map: department_role → general_role
    │   Example: "manager" (finance) → "analyst"
    │
    ├─ Check: ROLE_ACCESS[general_role] contains document.domain
    │
    └─ If denied: Document filtered out, never reaches LLM
        │
        ▼
PII Detection & Masking (BEFORE LLM sees data)
    │
    ├─ Detect sensitive patterns:
    │   - SSN: 123-45-6789
    │   - AccountNumber: AC847392
    │   - Email, Phone, etc.
    │
    ├─ Mask based on role:
    │   - admin/analyst: Less aggressive masking
    │   - employee/guest: Aggressive masking
    │
    └─ Masked document sent to LLM
```

## 📁 Directory Structure

```
agentic_system/
├── agent.py                 # ADK entry point (exports root_agent)
├── __init__.py              # Package initialization
│
├── base/                    # Base orchestrator agent
│   ├── agent.py            # Creates root agent with sub-agents
│   └── prompt.py           # Routing instructions
│
├── financial/              # Financial domain agent
│   ├── agent.py           # Financial agent implementation
│   └── prompt.py          # Financial-specific prompts
│
├── hr/                     # HR domain agent
│   ├── agent.py
│   └── prompt.py
│
├── health/                 # Health/HIPAA domain agent
│   ├── agent.py
│   └── prompt.py
│
├── law/                    # Legal domain agent
│   ├── agent.py
│   └── prompt.py
│
├── shared/                  # Shared components
│   ├── tools.py           # RAG tools (retrieve, validate, mask)
│   └── role_mapping.py    # Department roles → General roles mapping
│
└── utils/                  # Utilities
    └── llm.py             # LLM initialization (LiteLLM)
```

## 🤖 Domain Agents

### Financial Agent (`financial_agent`)
- **Purpose**: Handles financial performance, revenue, sales, and earnings queries
- **Domain**: `finance`
- **Available Roles**: `manager`, `analyst`, `employee`, `general`
- **Example Queries**:
  - "What were Q2 2024 revenue figures?"
  - "Show me sales performance by region"
  - "What is our EBITDA for the quarter?"

### HR Agent (`hr_agent`)
- **Purpose**: Handles employee benefits, policies, onboarding, and performance reviews
- **Domain**: `hr`
- **Available Roles**: `manager`, `hr_specialist`, `employee`, `general`
- **Example Queries**:
  - "What are our employee benefits?"
  - "Explain the performance review process"
  - "What is the PTO policy?"

### Health Agent (`health_agent`)
- **Purpose**: Handles healthcare, HIPAA compliance, patient privacy, and medical information
- **Domain**: `health`
- **Available Roles**: `manager`, `doctor`, `nurse`, `employee`, `general`
- **Example Queries**:
  - "What are HIPAA compliance requirements?"
  - "Explain patient data security protocols"
  - "What is the medical equipment maintenance schedule?"

### Law Agent (`law_agent`)
- **Purpose**: Handles legal contracts, compliance, and regulations
- **Domain**: `legal`
- **Available Roles**: `manager`, `legal_counsel`, `paralegal`, `employee`, `general`
- **Example Queries**:
  - "What are our contract management guidelines?"
  - "Explain liability limitations in contracts"

## 🔒 Security Features

### 1. Deterministic Access Control
- Access checks happen **before** data reaches the LLM
- Role-based permissions enforced programmatically
- Unauthorized documents are filtered out entirely

### 2. PII Masking
- Automatic detection of sensitive patterns (SSN, AccountNumber, etc.)
- Role-based masking intensity
- PII masked deterministically before LLM processing

### 3. Domain Isolation
- Each agent only accesses documents in its domain
- Cross-domain access requires explicit permissions
- Public domain documents accessible to all roles

### 4. Role Hierarchy
```
General Roles (for access control):
├── admin      → Full access to all domains
├── analyst    → Access to finance, hr, public
├── manager    → Access to hr, public
├── employee   → Access to public only
└── guest      → Access to public only
```

## 🚀 Quick Start

### Prerequisites

1. **Install Dependencies**:
```bash
pip install -r requirements.txt
```

2. **Set Environment Variables** (`.env` file):
```bash
OPENAI_API_KEY=your_openai_key_here
PINECONE_API_KEY=your_pinecone_key_here
```

3. **Ensure Documents are Indexed**:
The system uses `data/expanded_docs.json`. Documents are automatically indexed to Pinecone on first run.

### Running the System

**Start the ADK Web UI**:
```bash
cd /path/to/senior_seminar
adk web
```

The web UI will be available at `http://localhost:8000`

### Using the System

1. **Open the Web UI**: Navigate to `http://localhost:8000`
2. **Select the Agent**: Choose `agentic_system` from the app list
3. **Ask a Question**: Type your query in the chat interface
4. **Provide Role**: When prompted, specify your role in the department
5. **Get Answer**: Receive a response with proper access control and PII masking

## 💻 Usage Examples

### Example 1: Financial Query

```
User: "What were Q2 2024 revenue figures?"

Base Agent: 
  → Routes to financial_agent

Financial Agent:
  → "What is your role in the finance department? 
     Please choose one: manager, analyst, employee, or general"

User: "manager"

Financial Agent:
  → Maps: manager (finance) → analyst (general role)
  → Retrieves finance domain documents
  → Validates access (analyst can access finance domain)
  → Masks PII (AccountNumber AC847392 → [MASKED-ACCOUNT])
  → Returns: "Q2 2024 revenue was $45.2M, up 15% YoY..."
```

### Example 2: HR Query

```
User: "What are our employee benefits?"

Base Agent:
  → Routes to hr_agent

HR Agent:
  → "What is your role in the HR department?"

User: "employee"

HR Agent:
  → Maps: employee → employee (general role)
  → Retrieves HR domain documents
  → Validates access (employee can access hr domain)
  → Masks PII (salary ranges masked for employees)
  → Returns: "Our benefits package includes health insurance..."
```

## 📝 Code Snippets

### Creating the Root Agent

```python
from agentic_system.base.agent import create_trustworthy_rag_agent

# Create the root orchestrator agent
root_agent = create_trustworthy_rag_agent()

# The agent is ready to use with Google ADK
```

### Creating a Domain Agent

```python
from agentic_system.financial.agent import create_financial_agent
from retriever import HybridRetriever

# Initialize retriever
retriever = HybridRetriever(
    documents=documents,
    use_pinecone=True,
    pinecone_index_name="seniorseminar"
)

# Create financial agent
financial_agent = create_financial_agent(retriever)

# Agent has RAG tools automatically attached
```

### Using RAG Tools

```python
from agentic_system.shared.tools import create_rag_tools

# Create RAG tools for a domain
check_access, retrieve_and_validate, extract_info, mask_pii = create_rag_tools(
    retriever=retriever,
    domain="finance"
)

# Example: Retrieve and validate documents
docs = retrieve_and_validate(
    query="Q2 revenue figures",
    department_role="manager",
    k=5
)

# Documents are already validated and masked
# No unauthorized data or PII reaches the LLM
```

### Role Mapping

```python
from agentic_system.shared.role_mapping import get_role_for_access

# Map department role to general role
general_role = get_role_for_access("finance", "manager")
# Returns: "analyst"

general_role = get_role_for_access("health", "doctor")
# Returns: "analyst"

general_role = get_role_for_access("hr", "employee")
# Returns: "employee"
```

### Access Control Check

```python
from validator import check_access_permission

# Check if role has access to domain
has_access = check_access_permission("analyst", "finance")
# Returns: True (analyst can access finance domain)

has_access = check_access_permission("employee", "finance")
# Returns: False (employee cannot access finance domain)
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# OpenAI API (for LLM and embeddings)
OPENAI_API_KEY=sk-...

# Pinecone API (for vector database)
PINECONE_API_KEY=...

# Optional: Override default models
# DEFAULT_LLM_MODEL=openai/gpt-4o-mini
# POWERFUL_LLM_MODEL=openai/gpt-4o
```

### Document Structure

Documents in `data/expanded_docs.json` should follow this structure:

```json
{
  "id": "doc_001",
  "title": "Document Title",
  "content": "Document content...",
  "domain": "finance",  // or "hr", "health", "legal", "public"
  "author": "Author Name",
  "date": "2024-01-01",
  "classification": "confidential"  // or "internal", "public"
}
```

### Customizing Agents

To add a new domain agent:

1. **Create agent folder**:
```bash
mkdir agentic_system/new_domain
```

2. **Create agent.py**:
```python
from agentic_system.new_domain.prompt import NEW_DOMAIN_AGENT_FULL
from agentic_system.shared.tools import create_rag_tools

def create_new_domain_agent(retriever, api_key=None):
    llm = get_standard_llm(api_key=api_key)
    check_access, retrieve_and_validate, extract_info, mask_pii = create_rag_tools(
        retriever=retriever,
        domain="new_domain"
    )
    agent = LlmAgent(
        name="new_domain_agent",
        model=llm,
        instruction=NEW_DOMAIN_AGENT_FULL,
        tools=[check_access, retrieve_and_validate, extract_info, mask_pii]
    )
    return agent
```

3. **Add to base agent**:
```python
from agentic_system.new_domain.agent import create_new_domain_agent

new_domain_agent = create_new_domain_agent(retriever, api_key=api_key)

root_agent = LlmAgent(
    sub_agents=[
        financial_agent,
        hr_agent,
        health_agent,
        law_agent,
        new_domain_agent  # Add here
    ]
)
```

4. **Update role mapping**:
```python
DEPARTMENT_ROLE_MAPPING = {
    # ... existing mappings ...
    "new_domain": {
        "manager": "analyst",
        "specialist": "manager",
        "employee": "employee",
        "general": "guest"
    }
}
```

## 🔍 Key Components

### HybridRetriever
- **Semantic Search**: Pinecone vector database (1024-dim embeddings)
- **Keyword Search**: TF-IDF for exact keyword matching
- **Hybrid Scoring**: Weighted combination of both methods

### Validator
- **Access Control**: Role-based domain permissions
- **PII Detection**: Pattern-based sensitive data detection
- **Compliance**: HIPAA, GDPR validation rules

### RAG Tools
- **check_access**: Verify role permissions
- **retrieve_and_validate**: Retrieve + validate + mask in one call
- **extract_info**: Build context from validated documents
- **mask_pii_for_role**: Role-specific PII masking

## 🎯 Best Practices

1. **Always Use Sub-Agents**: Route queries through domain agents, never bypass them
2. **Role First**: Always ask for role before retrieving documents
3. **Trust Validation**: RAG tools handle security automatically - trust them
4. **Cite Sources**: Always cite document sources in responses

## 📚 Additional Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [Multi-Agent Systems in ADK](https://google.github.io/adk-docs/agents/multi-agents/)
- [LiteLLM Documentation](https://docs.litellm.ai/)

## 🐛 Troubleshooting

### Issue: "Pinecone index not found"
**Solution**: Documents are automatically indexed on first run. Ensure `PINECONE_API_KEY` is set.

### Issue: "validated_documents parameter is required"
**Solution**: Ensure `retrieve_and_validate` is called before `extract_info`. The system now handles this gracefully.

### Issue: "Access denied" messages
**Solution**: This is expected behavior. Users with lower roles cannot access restricted domains. Check role mappings in `shared/role_mapping.py`.

### Issue: ADK web UI not starting
**Solution**: Ensure you're in the project root directory and `agentic_system/agent.py` exports `root_agent`.

---

**Built with**: Google ADK, LiteLLM, Pinecone, OpenAI, LangChain

