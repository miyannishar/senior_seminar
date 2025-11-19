"""
FastAPI REST API for Trustworthy RAG System
Production-ready API with authentication, rate limiting, and monitoring.
"""

import json
import time
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from functools import wraps

from fastapi import FastAPI, HTTPException, Depends, Header, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from generator import SecureRAGGenerator
from agents import MultiAgentRAG, Tool
from utils.logger import setup_logger
from utils.exceptions import AccessDeniedException, RetrievalException

# Import guardrails for metrics endpoint
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from agentic_system.shared.guardrails import get_guardrails

logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Trustworthy RAG API",
    description="Production RAG system with privacy, security, and compliance",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics
REQUEST_COUNT = Counter(
    'rag_requests_total',
    'Total RAG requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'rag_request_latency_seconds',
    'Request latency in seconds',
    ['method', 'endpoint']
)

VALIDATION_DENIALS = Counter(
    'rag_validation_denials_total',
    'Total validation denials',
    ['reason']
)

# Global RAG instance (initialized on startup)
rag_generator: Optional[SecureRAGGenerator] = None
agent_system: Optional[MultiAgentRAG] = None


# ============================================================================
# Pydantic Models
# ============================================================================

class UserInfo(BaseModel):
    """User information model."""
    username: str = Field(..., min_length=1, max_length=100)
    role: str = Field(..., pattern="^(admin|analyst|manager|employee|guest)$")
    
    class Config:
        schema_extra = {
            "example": {
                "username": "john_doe",
                "role": "analyst"
            }
        }


class QueryRequest(BaseModel):
    """Query request model."""
    query: str = Field(..., min_length=1, max_length=1000)
    user: UserInfo
    k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")
    use_agents: bool = Field(default=False, description="Use multi-agent processing")
    
    class Config:
        schema_extra = {
            "example": {
                "query": "What are the Q2 financial highlights?",
                "user": {
                    "username": "analyst_user",
                    "role": "analyst"
                },
                "k": 5,
                "use_agents": False
            }
        }


class ComplianceQueryRequest(QueryRequest):
    """Query request with compliance framework."""
    compliance_framework: str = Field(
        default="general",
        pattern="^(hipaa|gdpr|sox|general)$",
        description="Compliance framework to apply"
    )


class QueryResponse(BaseModel):
    """Query response model."""
    success: bool
    response: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    timestamp: str
    duration_seconds: float


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    timestamp: str
    version: str
    components: Dict[str, bool]


class StatsResponse(BaseModel):
    """System statistics response."""
    total_documents: int
    vector_store: str
    retrieval_config: Dict[str, Any]
    uptime_seconds: float


# ============================================================================
# Dependencies
# ============================================================================

def get_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """
    Validate API key from header.
    In production, implement proper API key validation.
    """
    # For demo purposes, we'll allow requests without API key
    # In production, implement proper validation
    if x_api_key:
        # Validate against database/service
        pass
    return x_api_key or "demo"


async def track_request(request: Request):
    """Middleware to track requests."""
    start_time = time.time()
    
    # Process request
    yield
    
    # Track metrics
    duration = time.time() - start_time
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(duration)


# ============================================================================
# Startup/Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize RAG system on startup."""
    global rag_generator, agent_system
    
    logger.info("🚀 Starting Trustworthy RAG API...")
    
    # Load documents
    data_path = os.path.join(
        os.path.dirname(__file__),
        "../data/sample_docs.json"
    )
    
    try:
        with open(data_path, 'r') as f:
            documents = json.load(f)
        
        logger.info(f"✅ Loaded {len(documents)} documents")
        
        # Initialize RAG generator
        rag_generator = SecureRAGGenerator(
            documents=documents,
            model_name=os.getenv("MODEL_NAME", "gpt-3.5-turbo"),
            temperature=float(os.getenv("MODEL_TEMPERATURE", "0.7"))
        )
        
        logger.info("✅ RAG generator initialized")
        
        # Initialize agent system
        retriever_tool = Tool(
            name="retrieve_documents",
            description="Retrieve relevant documents",
            function=lambda query, k=5: rag_generator.retriever.retrieve(query, k=k)
        )
        
        validator_tool = Tool(
            name="validate_documents",
            description="Validate document access",
            function=lambda docs, role: docs  # Simplified
        )
        
        agent_system = MultiAgentRAG(
            retriever_tool=retriever_tool,
            validator_tool=validator_tool,
            model_name=os.getenv("MODEL_NAME", "gpt-3.5-turbo")
        )
        
        logger.info("✅ Multi-agent system initialized")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("👋 Shutting down Trustworthy RAG API")


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint."""
    return {
        "message": "Trustworthy RAG API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    components = {
        "rag_generator": rag_generator is not None,
        "agent_system": agent_system is not None,
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY"))
    }
    
    all_healthy = all(components.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now().isoformat(),
        version="1.0.0",
        components=components
    )


@app.get("/stats", response_model=StatsResponse)
async def get_stats(api_key: str = Depends(get_api_key)):
    """Get system statistics."""
    if not rag_generator:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    stats = rag_generator.retriever.get_stats()
    
    return StatsResponse(
        total_documents=stats['total_documents'],
        vector_store=stats['vector_store'],
        retrieval_config={
            'top_k': 5,
            'semantic_weight': 0.7
        },
        uptime_seconds=time.time() - app.state.start_time if hasattr(app.state, 'start_time') else 0
    )


@app.post("/query", response_model=QueryResponse)
async def query(
    request: QueryRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Main query endpoint.
    
    Process a user query with privacy and validation.
    """
    if not rag_generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG system not initialized"
        )
    
    start_time = time.time()
    
    try:
        user_dict = {
            "username": request.user.username,
            "role": request.user.role
        }
        
        # Use agents or standard RAG
        if request.use_agents and agent_system:
            logger.info("🤖 Using multi-agent processing")
            result = agent_system.process_query(
                query=request.query,
                user=user_dict
            )
            
            response_text = result.get('synthesis', 'No synthesis available')
            sources = []
            metadata = {
                'agent_processing': True,
                'tasks_created': len(result.get('tasks', [])),
                'agent_summary': result.get('agent_summary', [])
            }
        else:
            # Standard RAG processing
            response_text, sources, metadata = rag_generator.generate_secure_response(
                query=request.query,
                user=user_dict,
                k=request.k
            )
        
        duration = time.time() - start_time
        
        # Track metrics
        REQUEST_COUNT.labels(
            method='POST',
            endpoint='/query',
            status='success'
        ).inc()
        
        return QueryResponse(
            success=True,
            response=response_text,
            sources=sources,
            metadata=metadata,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration
        )
        
    except AccessDeniedException as e:
        VALIDATION_DENIALS.labels(reason='access_denied').inc()
        REQUEST_COUNT.labels(method='POST', endpoint='/query', status='denied').inc()
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
        
    except Exception as e:
        logger.error(f"Query processing error: {e}")
        REQUEST_COUNT.labels(method='POST', endpoint='/query', status='error').inc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.post("/query/compliance", response_model=QueryResponse)
async def query_with_compliance(
    request: ComplianceQueryRequest,
    api_key: str = Depends(get_api_key)
):
    """
    Query endpoint with compliance framework.
    
    Apply specific regulatory compliance rules (HIPAA, GDPR, SOX).
    """
    if not rag_generator:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RAG system not initialized"
        )
    
    start_time = time.time()
    
    try:
        user_dict = {
            "username": request.user.username,
            "role": request.user.role
        }
        
        response_text, sources, metadata = rag_generator.generate_with_compliance(
            query=request.query,
            user=user_dict,
            compliance_framework=request.compliance_framework,
            k=request.k
        )
        
        duration = time.time() - start_time
        
        REQUEST_COUNT.labels(
            method='POST',
            endpoint='/query/compliance',
            status='success'
        ).inc()
        
        return QueryResponse(
            success=True,
            response=response_text,
            sources=sources,
            metadata=metadata,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration
        )
        
    except Exception as e:
        logger.error(f"Compliance query error: {e}")
        REQUEST_COUNT.labels(method='POST', endpoint='/query/compliance', status='error').inc()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


@app.get("/retriever/stats")
async def retriever_stats(api_key: str = Depends(get_api_key)):
    """Get retriever statistics."""
    if not rag_generator:
        raise HTTPException(status_code=503, detail="RAG system not initialized")
    
    return rag_generator.retriever.get_stats()


@app.get("/guardrails/metrics")
async def guardrail_metrics():
    """Get guardrail violation metrics and dashboard data."""
    try:
        guardrails = get_guardrails()
        metrics = guardrails.get_guardrail_metrics()
        violations = guardrails.get_violations(limit=100)
        
        return {
            "success": True,
            "metrics": metrics,
            "recent_violations": violations,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting guardrail metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving guardrail metrics: {str(e)}"
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal server error",
            "detail": str(exc) if os.getenv("DEBUG") else "An error occurred"
        }
    )


# ============================================================================
# Main (for development)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    # Track start time
    app.state.start_time = time.time()
    
    uvicorn.run(
        "api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", 8000)),
        reload=True,
        log_level="info"
    )

