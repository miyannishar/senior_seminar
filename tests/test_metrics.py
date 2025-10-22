"""
Tests for Metrics Module
"""

import pytest
from utils.metrics import MetricsCollector, record_query_metrics, get_system_metrics


class TestMetricsCollector:
    """Tests for metrics collector."""
    
    def test_metrics_init(self):
        """Test metrics collector initialization."""
        collector = MetricsCollector(max_history=100)
        assert collector is not None
        assert collector.max_history == 100
    
    def test_record_query(self):
        """Test recording query metrics."""
        collector = MetricsCollector()
        
        collector.record_query(
            query="test query",
            user={"username": "test_user", "role": "analyst"},
            retrieval_time=0.1,
            validation_time=0.05,
            generation_time=0.5,
            documents_retrieved=5,
            documents_validated=3,
            documents_denied=2,
            success=True
        )
        
        assert len(collector.query_metrics) == 1
        assert collector.counters['total_queries'] == 1
        assert collector.counters['successful_queries'] == 1
    
    def test_system_metrics(self):
        """Test getting system metrics."""
        collector = MetricsCollector()
        
        # Record some queries
        for i in range(5):
            collector.record_query(
                query=f"query {i}",
                user={"username": f"user_{i}", "role": "analyst"},
                retrieval_time=0.1,
                validation_time=0.05,
                generation_time=0.5,
                documents_retrieved=5,
                documents_validated=3,
                documents_denied=2,
                success=True
            )
        
        metrics = collector.get_system_metrics()
        assert metrics.total_queries == 5
        assert metrics.successful_queries == 5
        assert metrics.avg_latency_ms > 0
    
    def test_security_events(self):
        """Test recording security events."""
        collector = MetricsCollector()
        
        collector.record_security_event("access_denied", {"user": "test", "domain": "finance"})
        collector.record_security_event("pii_detected", {"doc_id": "123"})
        
        summary = collector.get_security_summary()
        assert summary['access_denied'] == 1
        assert summary['pii_detected'] == 1
    
    def test_recent_queries(self):
        """Test getting recent queries."""
        collector = MetricsCollector()
        
        for i in range(10):
            collector.record_query(
                query=f"query {i}",
                user={"username": f"user_{i}", "role": "analyst"},
                retrieval_time=0.1,
                validation_time=0.05,
                generation_time=0.5,
                documents_retrieved=5,
                documents_validated=3,
                documents_denied=2,
                success=True
            )
        
        recent = collector.get_recent_queries(limit=5)
        assert len(recent) == 5
    
    def test_metrics_reset(self):
        """Test resetting metrics."""
        collector = MetricsCollector()
        
        collector.record_query(
            query="test",
            user={"username": "test", "role": "analyst"},
            retrieval_time=0.1,
            validation_time=0.05,
            generation_time=0.5,
            documents_retrieved=5,
            documents_validated=3,
            documents_denied=2,
            success=True
        )
        
        collector.reset_metrics()
        assert len(collector.query_metrics) == 0
        assert collector.counters['total_queries'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

