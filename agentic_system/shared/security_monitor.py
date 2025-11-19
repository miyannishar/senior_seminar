"""
Simple security monitoring - tracks access denials and alerts.
"""

import sys
import os
import json
import threading
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

from utils.logger import setup_logger

logger = setup_logger(__name__)


class SecurityMonitor:
    """Simple security monitoring - tracks excessive denials."""
    
    def __init__(self, max_denials_per_hour: int = 10):
        self.max_denials_per_hour = max_denials_per_hour
        self.user_denials = defaultdict(lambda: deque(maxlen=100))
        self.alerts = deque(maxlen=1000)
        
        # File-based persistence for alerts (shared between processes)
        alerts_dir = Path(__file__).parent.parent.parent / "data"
        alerts_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = alerts_dir / "alerts.json"
        self.alerts_lock = threading.Lock()
        self._last_file_mtime = 0
        
        # Load existing alerts from file
        self._load_alerts()
        
        logger.info("✅ SecurityMonitor initialized")
    
    def record_access_denial(
        self, 
        user: str, 
        session_id: str, 
        domain: str, 
        role: str, 
        query: str,
        reason: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Record access denial and create security alert."""
        now = datetime.now()
        self.user_denials[user].append(now)
        
        # Create security alert for every access denial
        alert = {
            "alert_type": "access_denied",
            "type": "ACCESS_DENIED",
            "timestamp": now.isoformat(),
            "user": user,
            "session_id": session_id,
            "message": f"Access denied: Role '{role}' attempted to access '{domain}' domain",
            "description": reason or f"Access denied for role '{role}' to domain '{domain}'",
            "severity": "MEDIUM",
            "domain": domain,
            "role": role,
            "query": query[:200] if query else None
        }
        self.add_alert(alert)
        logger.warning(f"🚨 Security Alert: Access denied - {user} ({role}) → {domain}")
        
        # Check for excessive denials (additional alert)
        recent = [t for t in self.user_denials[user] if (now - t).total_seconds() < 3600]
        
        if len(recent) >= self.max_denials_per_hour:
            excessive_alert = {
                "alert_type": "excessive_denials",
                "type": "EXCESSIVE_DENIALS",
                "timestamp": now.isoformat(),
                "user": user,
                "session_id": session_id,
                "message": f"Excessive access denials detected: {len(recent)} denials in last hour",
                "description": f"{len(recent)} denials in last hour for user {user}",
                "severity": "HIGH",
                "denial_count": len(recent)
            }
            self.add_alert(excessive_alert)
            logger.warning(f"🚨 Security Alert: Excessive denials for {user} - {len(recent)} in last hour")
            return excessive_alert
        
        return alert
    
    def _load_alerts(self) -> None:
        """Load alerts from file (only if file has changed)."""
        try:
            if not os.path.exists(self.alerts_file):
                return
            
            current_mtime = os.path.getmtime(self.alerts_file)
            if current_mtime == self._last_file_mtime:
                return  # File hasn't changed, skip reload
            
            with self.alerts_lock:
                with open(self.alerts_file, 'r') as f:
                    alerts_list = json.load(f)
                
                # Convert back to deque
                self.alerts = deque(alerts_list[-1000:], maxlen=1000)
                self._last_file_mtime = current_mtime
        except Exception as e:
            logger.debug(f"Could not load alerts from file: {e}")
            if not self.alerts:
                self.alerts = deque(maxlen=1000)
    
    def _save_alerts(self, skip_lock: bool = False) -> None:
        """Save alerts to file."""
        try:
            if skip_lock:
                # Lock already held by caller
                alerts_list = list(self.alerts)
                with open(self.alerts_file, 'w') as f:
                    json.dump(alerts_list, f, indent=2, default=str)
            else:
                with self.alerts_lock:
                    alerts_list = list(self.alerts)
                    with open(self.alerts_file, 'w') as f:
                        json.dump(alerts_list, f, indent=2, default=str)
            
            # Update modification time
            if os.path.exists(self.alerts_file):
                self._last_file_mtime = os.path.getmtime(self.alerts_file)
        except Exception as e:
            logger.error(f"❌ Could not save alerts to file: {e}")
    
    def add_alert(self, alert: Dict[str, Any]) -> None:
        """Add alert and persist to file."""
        with self.alerts_lock:
            self.alerts.append(alert)
            self._save_alerts(skip_lock=True)  # Persist to file immediately (lock already held)
    
    def get_alerts(self, severity: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        # Reload from file to get latest alerts from other processes (only if file changed)
        self._load_alerts()
        
        with self.alerts_lock:
            alerts = list(self.alerts)
        
        if severity:
            alerts = [a for a in alerts if a.get("severity") == severity]
        return alerts[-limit:]
    
    def create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "MEDIUM",
        user: str = "system",
        session_id: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Manually create a security alert."""
        alert = {
            "alert_type": alert_type,
            "type": alert_type,
            "timestamp": datetime.now().isoformat(),
            "user": user,
            "session_id": session_id,
            "message": message,
            "description": message,
            "severity": severity,
            **kwargs
        }
        self.add_alert(alert)
        logger.warning(f"🚨 Security Alert Created: {alert_type} - {message}")
        return alert
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """Get security metrics."""
        # Reload from file to get latest alerts from other processes (only if file changed)
        self._load_alerts()
        
        with self.alerts_lock:
            alerts_list = list(self.alerts)
        
        return {
            "total_alerts": len(alerts_list),
            "critical_alerts": len([a for a in alerts_list if a.get("severity") == "CRITICAL"]),
            "high_alerts": len([a for a in alerts_list if a.get("severity") == "HIGH"]),
            "medium_alerts": len([a for a in alerts_list if a.get("severity") == "MEDIUM"]),
            "low_alerts": len([a for a in alerts_list if a.get("severity") == "LOW"])
        }


# Global instance
_security_monitor: Optional[SecurityMonitor] = None

def get_security_monitor() -> SecurityMonitor:
    """Get or create global security monitor."""
    global _security_monitor
    if _security_monitor is None:
        _security_monitor = SecurityMonitor()
    return _security_monitor
