"""
Metrics and Monitoring Module
Track performance, usage, and security metrics for the RAG system.
"""

import time
import statistics
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
from datetime import datetime
import json

from utils.logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class QueryMetrics:
    """Metrics for a single query."""
    query_id: str
    timestamp: str
    user: str
    user_role: str
    query_length: int
    retrieval_time_ms: float
    validation_time_ms: float
    generation_time_ms: float
    total_time_ms: float
    documents_retrieved: int
    documents_validated: int
    documents_denied: int
    success: bool
    error: Optional[str] = None


@dataclass
class SystemMetrics:
    """Aggregate system metrics."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    total_documents_retrieved: int = 0
    total_validation_denials: int = 0
    queries_by_role: Dict[str, int] = field(default_factory=dict)
    queries_by_hour: Dict[str, int] = field(default_factory=dict)


class MetricsCollector:
    """
    Collects and aggregates metrics for the RAG system.
    """
    
    def __init__(self, max_history: int = 1000):
        """
        Initialize metrics collector.
        
        Args:
            max_history: Maximum number of query metrics to keep in memory
        """
        self.max_history = max_history
        self.query_metrics: deque = deque(maxlen=max_history)
        self.start_time = time.time()
        
        # Counters
        self.counters = defaultdict(int)
        
        # Latency tracking
        self.latencies: deque = deque(maxlen=max_history)
        
        # Security metrics
        self.security_events = defaultdict(int)
        
        logger.info(f"✅ MetricsCollector initialized (max_history={max_history})")
    
    def record_query(
        self,
        query: str,
        user: Dict[str, str],
        retrieval_time: float,
        validation_time: float,
        generation_time: float,
        documents_retrieved: int,
        documents_validated: int,
        documents_denied: int,
        success: bool,
        error: Optional[str] = None
    ):
        """Record metrics for a query."""
        total_time = retrieval_time + validation_time + generation_time
        
        metrics = QueryMetrics(
            query_id=f"q_{int(time.time() * 1000)}",
            timestamp=datetime.now().isoformat(),
            user=user.get('username', 'unknown'),
            user_role=user.get('role', 'unknown'),
            query_length=len(query),
            retrieval_time_ms=retrieval_time * 1000,
            validation_time_ms=validation_time * 1000,
            generation_time_ms=generation_time * 1000,
            total_time_ms=total_time * 1000,
            documents_retrieved=documents_retrieved,
            documents_validated=documents_validated,
            documents_denied=documents_denied,
            success=success,
            error=error
        )
        
        self.query_metrics.append(metrics)
        self.latencies.append(total_time * 1000)
        
        # Update counters
        self.counters['total_queries'] += 1
        if success:
            self.counters['successful_queries'] += 1
        else:
            self.counters['failed_queries'] += 1
        
        self.counters[f'queries_by_role_{user.get("role", "unknown")}'] += 1
        self.counters['total_documents_retrieved'] += documents_retrieved
        self.counters['total_validation_denials'] += documents_denied
        
        # Track by hour
        hour_key = datetime.now().strftime('%Y-%m-%d-%H')
        self.counters[f'queries_hour_{hour_key}'] += 1
        
        logger.debug(f"📊 Recorded query metrics: {metrics.query_id}")
    
    def record_security_event(self, event_type: str, details: Dict[str, Any]):
        """Record a security event."""
        self.security_events[event_type] += 1
        logger.info(f"🔒 Security event: {event_type} - {details}")
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get aggregate system metrics."""
        if not self.latencies:
            return SystemMetrics()
        
        latencies_sorted = sorted(self.latencies)
        n = len(latencies_sorted)
        
        # Calculate percentiles
        p50_idx = int(n * 0.50)
        p95_idx = int(n * 0.95)
        p99_idx = int(n * 0.99)
        
        # Queries by role
        queries_by_role = {}
        for key, value in self.counters.items():
            if key.startswith('queries_by_role_'):
                role = key.replace('queries_by_role_', '')
                queries_by_role[role] = value
        
        # Queries by hour
        queries_by_hour = {}
        for key, value in self.counters.items():
            if key.startswith('queries_hour_'):
                hour = key.replace('queries_hour_', '')
                queries_by_hour[hour] = value
        
        return SystemMetrics(
            total_queries=self.counters['total_queries'],
            successful_queries=self.counters['successful_queries'],
            failed_queries=self.counters['failed_queries'],
            avg_latency_ms=statistics.mean(self.latencies) if self.latencies else 0.0,
            p50_latency_ms=latencies_sorted[p50_idx] if n > 0 else 0.0,
            p95_latency_ms=latencies_sorted[p95_idx] if n > 0 else 0.0,
            p99_latency_ms=latencies_sorted[p99_idx] if n > 0 else 0.0,
            total_documents_retrieved=self.counters['total_documents_retrieved'],
            total_validation_denials=self.counters['total_validation_denials'],
            queries_by_role=queries_by_role,
            queries_by_hour=queries_by_hour
        )
    
    def get_recent_queries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent query metrics."""
        recent = list(self.query_metrics)[-limit:]
        return [
            {
                'query_id': m.query_id,
                'timestamp': m.timestamp,
                'user': m.user,
                'role': m.user_role,
                'total_time_ms': m.total_time_ms,
                'documents_retrieved': m.documents_retrieved,
                'documents_validated': m.documents_validated,
                'success': m.success
            }
            for m in recent
        ]
    
    def get_security_summary(self) -> Dict[str, int]:
        """Get security event summary."""
        return dict(self.security_events)
    
    def export_metrics(self, filepath: str):
        """Export all metrics to a file."""
        data = {
            'system_metrics': self.get_system_metrics().__dict__,
            'recent_queries': self.get_recent_queries(limit=100),
            'security_events': self.get_security_summary(),
            'uptime_seconds': time.time() - self.start_time,
            'export_timestamp': datetime.now().isoformat()
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"📊 Metrics exported to {filepath}")
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        self.query_metrics.clear()
        self.latencies.clear()
        self.counters.clear()
        self.security_events.clear()
        self.start_time = time.time()
        logger.info("🔄 Metrics reset")


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def record_query_metrics(**kwargs):
    """Convenience function to record query metrics."""
    collector = get_metrics_collector()
    collector.record_query(**kwargs)


def record_security_event(event_type: str, details: Dict[str, Any]):
    """Convenience function to record security events."""
    collector = get_metrics_collector()
    collector.record_security_event(event_type, details)


def get_system_metrics() -> SystemMetrics:
    """Convenience function to get system metrics."""
    collector = get_metrics_collector()
    return collector.get_system_metrics()

