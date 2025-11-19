"""
Simple audit logging for compliance.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

from utils.logger import setup_logger

logger = setup_logger(__name__)


class AuditLogger:
    """Simple audit logger."""
    
    def __init__(self, max_events: int = 10000):
        self.events = deque(maxlen=max_events)
        self.metrics = defaultdict(int)
        logger.info("✅ AuditLogger initialized")
    
    def log_access_attempt(self, user: str, user_role: str, domain: str, decision: str, document_id: Optional[str] = None, reason: Optional[str] = None):
        """Log access attempt."""
        event = {
            "event_type": "access_control",
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "user_role": user_role,
            "domain": domain,
            "decision": decision,
            "document_id": document_id,
            "reason": reason
        }
        self.events.append(event)
        self.metrics[f"access_{decision}"] += 1
        logger.info(f"📝 Audit: {decision.upper()} - {user_role} → {domain}")
    
    def log_query(self, user: str, user_role: str, query: str, domain: str, documents_retrieved: int, documents_validated: int, response_time_ms: float = 0):
        """Log query."""
        event = {
            "event_type": "query",
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "user_role": user_role,
            "query": query,
            "domain": domain,
            "documents_retrieved": documents_retrieved,
            "documents_validated": documents_validated
        }
        self.events.append(event)
        self.metrics["total_queries"] += 1
        logger.info(f"📊 Audit: Query logged - {domain}")
    
    def get_compliance_report(self, framework: str = "general", time_period_days: int = 30) -> Dict[str, Any]:
        """Generate simple compliance report."""
        cutoff_time = datetime.now() - timedelta(days=time_period_days)
        recent_events = [e for e in self.events if datetime.fromisoformat(e["timestamp"]) >= cutoff_time]
        
        access_attempts = len([e for e in recent_events if e["event_type"] == "access_control"])
        access_granted = len([e for e in recent_events if e["event_type"] == "access_control" and e["decision"] == "granted"])
        access_denied = len([e for e in recent_events if e["event_type"] == "access_control" and e["decision"] == "denied"])
        queries_total = len([e for e in recent_events if e["event_type"] == "query"])
        
        return {
            "framework": framework.upper(),
            "period": f"Last {time_period_days} days",
            "summary": {
                "total_access_attempts": access_attempts,
                "access_granted": access_granted,
                "access_denied": access_denied,
                "total_queries": queries_total
            },
            "status": "COMPLIANT"
        }


# Global instance
_audit_logger: Optional[AuditLogger] = None

def get_audit_logger() -> AuditLogger:
    """Get or create global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
