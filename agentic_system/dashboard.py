"""
Guardrails & Security Dashboard API
Separate FastAPI app for monitoring guardrail violations and security metrics.
"""

import os
import sys
from typing import Dict, Any, List, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Add paths for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../src'))

from agentic_system.shared.guardrails import get_guardrails
from agentic_system.shared.audit import get_audit_logger
from agentic_system.shared.security_monitor import get_security_monitor
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Guardrails & Security Dashboard",
    description="Real-time monitoring for guardrail violations and security metrics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    @app.get("/")
    async def dashboard_frontend():
        """Serve the dashboard frontend."""
        from fastapi.responses import FileResponse
        index_path = os.path.join(static_dir, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "Dashboard frontend not found"}


# ============================================================================
# Response Models
# ============================================================================

class GuardrailMetricsResponse(BaseModel):
    """Guardrail metrics response."""
    success: bool
    metrics: Dict[str, Any]
    recent_violations: List[Dict[str, Any]]
    timestamp: str


class SecurityMetricsResponse(BaseModel):
    """Security metrics response."""
    success: bool
    security_alerts: List[Dict[str, Any]]
    access_denials: int
    timestamp: str


class DashboardResponse(BaseModel):
    """Complete dashboard response."""
    success: bool
    guardrails: Dict[str, Any]
    security: Dict[str, Any]
    audit: Dict[str, Any]
    timestamp: str


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/info", response_model=Dict[str, str])
async def api_info():
    """API info endpoint."""
    return {
        "service": "Guardrails & Security Dashboard",
        "version": "1.0.0",
        "endpoints": {
            "metrics": "/guardrails/metrics",
            "violations": "/guardrails/violations",
            "security": "/security/metrics",
            "dashboard": "/dashboard",
            "docs": "/docs"
        }
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/guardrails/metrics", response_model=GuardrailMetricsResponse)
async def get_guardrail_metrics(
    severity: Optional[str] = None,
    violation_type: Optional[str] = None,
    limit: int = 100
):
    """Get guardrail violation metrics and dashboard data."""
    try:
        guardrails = get_guardrails()
        metrics = guardrails.get_guardrail_metrics()
        violations = guardrails.get_violations(
            severity=severity,
            violation_type=violation_type,
            limit=limit
        )
        
        return GuardrailMetricsResponse(
            success=True,
            metrics=metrics,
            recent_violations=violations,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting guardrail metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving guardrail metrics: {str(e)}"
        )


@app.get("/guardrails/violations")
async def get_violations(
    severity: Optional[str] = None,
    violation_type: Optional[str] = None,
    limit: int = 50
):
    """Get recent guardrail violations."""
    try:
        guardrails = get_guardrails()
        violations = guardrails.get_violations(
            severity=severity,
            violation_type=violation_type,
            limit=limit
        )
        
        return {
            "success": True,
            "violations": violations,
            "count": len(violations),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting violations: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving violations: {str(e)}"
        )


@app.get("/security/metrics", response_model=SecurityMetricsResponse)
async def get_security_metrics(severity: Optional[str] = None):
    """Get security monitoring metrics."""
    try:
        security_monitor = get_security_monitor()
        alerts = security_monitor.get_alerts(severity=severity)
        metrics = security_monitor.get_security_metrics()
        
        return SecurityMetricsResponse(
            success=True,
            security_alerts=alerts,
            access_denials=metrics.get("access_denials", 0),
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting security metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving security metrics: {str(e)}"
        )


@app.get("/dashboard", response_model=DashboardResponse)
async def get_full_dashboard():
    """Get complete dashboard with all metrics."""
    try:
        guardrails = get_guardrails()
        security_monitor = get_security_monitor()
        audit_logger = get_audit_logger()
        
        # Guardrail metrics
        guardrail_metrics = guardrails.get_guardrail_metrics()
        recent_violations = guardrails.get_violations(limit=20)
        
        # Security metrics
        security_alerts = security_monitor.get_alerts()
        security_metrics = security_monitor.get_security_metrics()
        
        # Audit summary (if available)
        audit_summary = {
            "total_events": len(audit_logger.events) if hasattr(audit_logger, 'events') else 0,
            "metrics": dict(audit_logger.metrics) if hasattr(audit_logger, 'metrics') else {}
        }
        
        return DashboardResponse(
            success=True,
            guardrails={
                "metrics": guardrail_metrics,
                "recent_violations": recent_violations
            },
            security={
                "alerts": security_alerts,
                "metrics": security_metrics
            },
            audit=audit_summary,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error getting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving dashboard: {str(e)}"
        )


# ============================================================================
# Error Handlers
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
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
    
    logger.info("=" * 60)
    logger.info("🚀 Starting Guardrails & Security Dashboard")
    logger.info("=" * 60)
    logger.info("📊 Dashboard available at: http://localhost:8001")
    logger.info("📚 API docs available at: http://localhost:8001/docs")
    logger.info("=" * 60)
    
    uvicorn.run(
        "dashboard:app",
        host="0.0.0.0",
        port=int(os.getenv("DASHBOARD_PORT", 8001)),
        reload=True,
        log_level="info"
    )

