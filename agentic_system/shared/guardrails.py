"""
Guardrails for Trustworthy AI - Simple Implementation.

Uses:
- Presidio for PII detection and masking
- GPT-4o-mini with system prompt for toxicity/vulgar language detection
- Rate limiting for abuse prevention
"""

import sys
import os
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import threading

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))

from utils.logger import setup_logger

logger = setup_logger(__name__)

# Import Presidio for PII detection
try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine
    PRESIDIO_AVAILABLE = True
    logger.info("✅ Presidio loaded for PII detection")
except ImportError:
    PRESIDIO_AVAILABLE = False
    logger.warning("⚠️  Presidio not available. Install with: pip install presidio-analyzer presidio-anonymizer")

# Import OpenAI for content moderation
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    logger.info("✅ OpenAI loaded for content moderation")
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("⚠️  OpenAI not available. Install with: pip install openai")


class GuardrailViolationType(Enum):
    """Types of guardrail violations."""
    PII_DETECTED = "pii_detected"
    TOXIC_CONTENT = "toxic_content"
    RATE_LIMIT_EXCEEDED = "rate_limit_exceeded"


class GuardrailSeverity(Enum):
    """Severity levels for guardrail violations."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"


# System prompt for content moderation
CONTENT_MODERATION_PROMPT = """You are a content moderation system. Analyze the given text and determine if it contains:
- Toxic language
- Vulgar/profane language
- Hate speech
- Harassment
- Violence

Respond with ONLY one word: "SAFE" or "UNSAFE"
Do not provide any explanation, just the single word response."""


class Guardrails:
    """
    Simple guardrails system:
    - Presidio for PII detection/masking
    - GPT-4o-mini for content moderation
    - Rate limiting
    """
    
    def __init__(
        self,
        enable_pii_detection: bool = True,
        enable_content_moderation: bool = True,
        enable_rate_limiting: bool = True,
        max_requests_per_minute: int = 60,
        max_requests_per_user_per_hour: int = 100,
        openai_api_key: Optional[str] = None
    ):
        """Initialize guardrails system."""
        self.enable_pii_detection = enable_pii_detection
        self.enable_content_moderation = enable_content_moderation
        self.enable_rate_limiting = enable_rate_limiting
        
        # Rate limiting
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_user_per_hour = max_requests_per_user_per_hour
        self.global_requests = deque(maxlen=1000)
        self.user_requests = defaultdict(lambda: deque(maxlen=200))
        
        # Violation tracking with file persistence
        self.violations_file = os.path.join(
            os.path.dirname(__file__),
            '../../violations.json'
        )
        self.violations_lock = threading.Lock()
        self.violations = deque(maxlen=1000)
        self._last_file_mtime = 0  # Track file modification time to avoid unnecessary reloads
        self._load_violations()
        
        # Initialize Presidio
        if PRESIDIO_AVAILABLE and self.enable_pii_detection:
            try:
                self.pii_analyzer = AnalyzerEngine()
                self.pii_anonymizer = AnonymizerEngine()
                logger.info("✅ Presidio initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Presidio: {e}")
                self.pii_analyzer = None
                self.pii_anonymizer = None
        else:
            self.pii_analyzer = None
            self.pii_anonymizer = None
        
        # Initialize OpenAI client
        if OPENAI_AVAILABLE and self.enable_content_moderation:
            try:
                if openai_api_key is None:
                    openai_api_key = os.getenv("OPENAI_API_KEY")
                self.openai_client = OpenAI(api_key=openai_api_key)
                logger.info("✅ OpenAI client initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize OpenAI: {e}")
                self.openai_client = None
        else:
            self.openai_client = None
        
        logger.info("✅ Guardrails initialized")
    
    def validate_input(
        self,
        query: str,
        user: str,
        role: str,
        domain: str,
        session_id: Optional[str] = None,
        store_query: bool = True
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate user input before processing."""
        # Rate limiting
        if self.enable_rate_limiting:
            rate_check, rate_violation = self._check_rate_limits(user)
            if not rate_check:
                logger.warning(f"Rate limit violation: {rate_violation.get('description')}")
                self._record_violation(rate_violation, user, session_id, query if store_query else None)
                return False, rate_violation
        
        # Content moderation
        if self.enable_content_moderation and self.openai_client:
            content_check, content_violation = self._moderate_content(query)
            if not content_check:
                logger.warning(f"Content violation: {content_violation.get('violation_type')} - {content_violation.get('description')}")
                self._record_violation(content_violation, user, session_id, query if store_query else None)
                return False, content_violation
        
        return True, None
    
    def validate_output(
        self,
        response: str,
        user: str,
        role: str,
        domain: str,
        original_query: Optional[str] = None,
        session_id: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate LLM output before returning to user."""
        # PII detection (for non-admin roles)
        if self.enable_pii_detection and self.pii_analyzer:
            if role not in ['admin', 'analyst']:
                pii_check, pii_violation = self._detect_pii(response, role)
                if not pii_check:
                    self._record_violation(pii_violation, user, session_id)
                    return False, pii_violation
        
        # Content moderation
        if self.enable_content_moderation and self.openai_client:
            content_check, content_violation = self._moderate_content(response)
            if not content_check:
                self._record_violation(content_violation, user, session_id)
                return False, content_violation
        
        return True, None
    
    def _check_rate_limits(self, user: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Check if rate limits are exceeded."""
        now = datetime.now()
        
        # Global rate limit
        self.global_requests.append(now)
        recent_global = sum(1 for t in self.global_requests if (now - t).total_seconds() < 60)
        
        if recent_global > self.max_requests_per_minute:
            violation = self._create_violation(
                GuardrailViolationType.RATE_LIMIT_EXCEEDED,
                GuardrailSeverity.HIGH,
                f"Global rate limit exceeded: {recent_global} requests per minute"
            )
            return False, violation
        
        # Per-user rate limit
        self.user_requests[user].append(now)
        recent_user = sum(1 for t in self.user_requests[user] if (now - t).total_seconds() < 3600)
        
        if recent_user > self.max_requests_per_user_per_hour:
            violation = self._create_violation(
                GuardrailViolationType.RATE_LIMIT_EXCEEDED,
                GuardrailSeverity.MEDIUM,
                f"User rate limit exceeded: {recent_user} requests per hour",
                user=user
            )
            return False, violation
        
        return True, None
    
    def _moderate_content(self, text: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Use GPT-4o-mini to check for toxic/vulgar content."""
        if not self.openai_client:
            return True, None
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": CONTENT_MODERATION_PROMPT},
                    {"role": "user", "content": text}
                ],
                temperature=0.0,
                max_tokens=10
            )
            
            result = response.choices[0].message.content.strip().upper()
            
            if result == "UNSAFE":
                violation = self._create_violation(
                    GuardrailViolationType.TOXIC_CONTENT,
                    GuardrailSeverity.HIGH,
                    "Content flagged as toxic/vulgar by GPT-4o-mini"
                )
                return False, violation
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error in content moderation: {e}")
            # Fail open - don't block if API fails
            return True, None
    
    def _detect_pii(self, text: str, role: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Use Presidio to detect PII in text."""
        if not self.pii_analyzer:
            return True, None
        
        try:
            results = self.pii_analyzer.analyze(
                text=text,
                language='en',
                entities=[
                    "PERSON", "EMAIL_ADDRESS", "PHONE_NUMBER", 
                    "CREDIT_CARD", "US_SSN", "US_DRIVER_LICENSE",
                    "IBAN_CODE", "IP_ADDRESS", "MEDICAL_LICENSE"
                ]
            )
            
            if results:
                detected_entities = [r.entity_type for r in results]
                violation = self._create_violation(
                    GuardrailViolationType.PII_DETECTED,
                    GuardrailSeverity.CRITICAL,
                    f"PII detected: {', '.join(set(detected_entities))}",
                    entities=detected_entities,
                    count=len(results),
                    role=role
                )
                logger.critical(f"🚨 PII detected for role: {role}")
                return False, violation
            
            return True, None
            
        except Exception as e:
            logger.error(f"Error in PII detection: {e}")
            return True, None
    
    def mask_pii(self, text: str) -> str:
        """Use Presidio to mask PII in text."""
        if not self.pii_analyzer or not self.pii_anonymizer:
            return text
        
        try:
            results = self.pii_analyzer.analyze(text=text, language='en')
            
            if results:
                anonymized_result = self.pii_anonymizer.anonymize(
                    text=text,
                    analyzer_results=results
                )
                return anonymized_result.text
            
            return text
            
        except Exception as e:
            logger.error(f"Error in PII masking: {e}")
            return text
    
    def _create_violation(
        self,
        violation_type: GuardrailViolationType,
        severity: GuardrailSeverity,
        description: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a violation record."""
        return {
            "violation_type": violation_type.value,
            "severity": severity.value,
            "description": description,
            "timestamp": datetime.now().isoformat(),
            "additional_data": kwargs
        }
    
    def _load_violations(self, force: bool = False) -> None:
        """Load violations from file. Only reloads if file has been modified."""
        try:
            if not os.path.exists(self.violations_file):
                return
            
            # Check file modification time to avoid unnecessary reloads
            current_mtime = os.path.getmtime(self.violations_file)
            if not force and current_mtime == self._last_file_mtime:
                return  # File hasn't changed, skip reload
            
            with open(self.violations_file, 'r') as f:
                violations_data = json.load(f)
                # Convert back to deque
                with self.violations_lock:
                    self.violations = deque(violations_data[-1000:], maxlen=1000)
                    self._last_file_mtime = current_mtime
                    logger.debug(f"✅ Loaded {len(self.violations)} violations from file")
        except Exception as e:
            logger.warning(f"⚠️  Could not load violations from file: {e}")
            if not self.violations:
                self.violations = deque(maxlen=1000)
    
    def _save_violations(self, skip_lock: bool = False) -> None:
        """Save violations to file."""
        try:
            if skip_lock:
                # Lock already held by caller
                violations_list = list(self.violations)
                with open(self.violations_file, 'w') as f:
                    json.dump(violations_list, f, indent=2, default=str)
            else:
                with self.violations_lock:
                    violations_list = list(self.violations)
                    with open(self.violations_file, 'w') as f:
                        json.dump(violations_list, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"❌ Could not save violations to file: {e}")
    
    def _record_violation(
        self,
        violation: Dict[str, Any],
        user: str,
        session_id: Optional[str],
        query: Optional[str] = None
    ) -> None:
        """Record a violation for auditing."""
        violation["user"] = user
        violation["username"] = user  # Alias for frontend
        violation["session_id"] = session_id
        violation["recorded_at"] = datetime.now().isoformat()
        violation["timestamp"] = violation["recorded_at"]  # Alias for frontend
        if query:
            violation["query"] = query
            violation["user_message"] = query  # Alias for frontend
        
        with self.violations_lock:
            self.violations.append(violation)
            self._save_violations(skip_lock=True)  # Persist to file immediately (lock already held)
            # Update modification time to reflect we just saved
            if os.path.exists(self.violations_file):
                self._last_file_mtime = os.path.getmtime(self.violations_file)
        
        logger.warning(f"Violation recorded: {violation.get('violation_type')} - {violation.get('description')} (User: {user})")
        
        # Generate security alert for critical/high severity violations
        violation_severity = violation.get('severity', 'LOW')
        if violation_severity in ['CRITICAL', 'HIGH']:
            try:
                from agentic_system.shared.security_monitor import get_security_monitor
                security_monitor = get_security_monitor()
                alert = {
                    "alert_type": f"guardrail_{violation.get('violation_type', 'VIOLATION').lower()}",
                    "type": violation.get('violation_type', 'GUARDRAIL_VIOLATION'),
                    "timestamp": violation.get('recorded_at', datetime.now().isoformat()),
                    "user": user,
                    "session_id": session_id,
                    "message": f"Guardrail violation: {violation.get('description', 'Security violation detected')}",
                    "description": violation.get('description', 'Security violation detected'),
                    "severity": violation_severity,
                    "violation_type": violation.get('violation_type'),
                    "query": query[:200] if query else None
                }
                security_monitor.add_alert(alert)
                logger.warning(f"🚨 Security alert generated for {violation_severity} violation: {violation.get('violation_type')}")
            except Exception as e:
                logger.debug(f"Could not create security alert: {e}")
    
    def get_violations(
        self,
        severity: Optional[str] = None,
        violation_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent violations."""
        # Reload from file to get latest violations from other processes (only if file changed)
        self._load_violations()
        
        with self.violations_lock:
            violations = list(self.violations)
        
        if severity:
            violations = [v for v in violations if v.get("severity") == severity]
        
        if violation_type:
            violations = [v for v in violations if v.get("violation_type") == violation_type]
        
        return violations[-limit:]
    
    def get_guardrail_metrics(self) -> Dict[str, Any]:
        """Get guardrail metrics."""
        # Reload from file to get latest violations from other processes (only if file changed)
        self._load_violations()
        
        with self.violations_lock:
            violations_list = list(self.violations)
        
        total_violations = len(violations_list)
        
        violations_by_severity = defaultdict(int)
        violations_by_type = defaultdict(int)
        
        for v in violations_list:
            violations_by_severity[v.get("severity", "UNKNOWN")] += 1
            violations_by_type[v.get("violation_type", "UNKNOWN")] += 1
        
        return {
            "total_violations": total_violations,
            "violations_by_severity": dict(violations_by_severity),
            "violations_by_type": dict(violations_by_type),
            "critical_violations": violations_by_severity.get("CRITICAL", 0),
            "high_violations": violations_by_severity.get("HIGH", 0),
            "pii_detection_enabled": self.enable_pii_detection and self.pii_analyzer is not None,
            "content_moderation_enabled": self.enable_content_moderation and self.openai_client is not None,
            "rate_limiting_enabled": self.enable_rate_limiting
        }


# Global guardrails instance
_guardrails: Optional[Guardrails] = None


def get_guardrails() -> Guardrails:
    """Get or create global guardrails instance."""
    global _guardrails
    if _guardrails is None:
        _guardrails = Guardrails()
    return _guardrails


def create_guardrail_tools():
    """Create ADK-compatible guardrail tools for agents."""
    guardrails = get_guardrails()
    
    def check_input_safety(
        query: str,
        user: str = "unknown",
        role: str = "employee",
        domain: str = "unknown"
    ) -> Dict[str, Any]:
        """Check if input query is safe before processing."""
        is_safe, violation = guardrails.validate_input(
            query=query,
            user=user,
            role=role,
            domain=domain
        )
        
        return {
            "is_safe": is_safe,
            "passed_validation": is_safe,
            "violation": violation,
            "message": "Query is safe" if is_safe else f"Validation failed: {violation['description']}"
        }
    
    def check_output_safety(
        response: str,
        user: str = "unknown",
        role: str = "employee",
        domain: str = "unknown"
    ) -> Dict[str, Any]:
        """Check if output response is safe before returning to user."""
        is_safe, violation = guardrails.validate_output(
            response=response,
            user=user,
            role=role,
            domain=domain
        )
        
        return {
            "is_safe": is_safe,
            "passed_validation": is_safe,
            "violation": violation,
            "message": "Response is safe" if is_safe else f"Validation failed: {violation['description']}"
        }
    
    def get_guardrail_status() -> Dict[str, Any]:
        """Get guardrail system status and metrics."""
        return guardrails.get_guardrail_metrics()
    
    def mask_pii_in_text(text: str) -> str:
        """Mask PII in text using Presidio."""
        return guardrails.mask_pii(text)
    
    return (
        check_input_safety,
        check_output_safety,
        get_guardrail_status,
        mask_pii_in_text
    )
