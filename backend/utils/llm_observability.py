"""
LLM Observability Module
Provides monitoring, metrics, and tracing for LLM calls using OpenTelemetry
"""
import time
import json
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, asdict
from datetime import datetime
import os

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class LLMMetrics:
    """Data class for LLM call metrics"""
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    latency_ms: float
    cost_estimate: float
    status: str
    error_message: Optional[str] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

class LLMObservability:
    """LLM Observability manager for monitoring LLM calls"""
    
    def __init__(self):
        self.enabled = os.getenv("LLM_OBSERVABILITY_ENABLED", "true").lower() == "true"
        self.metrics_storage = []
        self._setup_telemetry()
        
    def _setup_telemetry(self):
        """Setup OpenTelemetry tracing and metrics"""
        if not self.enabled:
            return
            
        try:
            # Setup resource
            resource = Resource.create({
                "service.name": "wingily-llm-service",
                "service.version": "1.0.0"
            })
            
            # Setup tracing
            trace.set_tracer_provider(TracerProvider(resource=resource))
            self.tracer = trace.get_tracer(__name__)
            
            logger.info("✅ LLM Observability initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to setup LLM observability: {e}")
            self.enabled = False

    def track_llm_call(self, 
                      model: str = "unknown",
                      provider: str = "unknown") -> Callable:
        """Decorator to track LLM calls"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                if not self.enabled:
                    return func(*args, **kwargs)
                
                start_time = time.time()
                
                try:
                    result = func(*args, **kwargs)
                    latency_ms = (time.time() - start_time) * 1000
                    
                    metrics_data = LLMMetrics(
                        model=model,
                        provider=provider,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        latency_ms=latency_ms,
                        cost_estimate=0.001,
                        status="success"
                    )
                    
                    self.metrics_storage.append(asdict(metrics_data))
                    logger.info(f"LLM call completed: {model} - {latency_ms:.2f}ms")
                    
                    return result
                    
                except Exception as e:
                    latency_ms = (time.time() - start_time) * 1000
                    
                    metrics_data = LLMMetrics(
                        model=model,
                        provider=provider,
                        prompt_tokens=0,
                        completion_tokens=0,
                        total_tokens=0,
                        latency_ms=latency_ms,
                        cost_estimate=0.0,
                        status="error",
                        error_message=str(e)
                    )
                    
                    self.metrics_storage.append(asdict(metrics_data))
                    logger.error(f"LLM call failed: {model} - {str(e)}")
                    raise
                    
            return wrapper
        return decorator

    def get_metrics_summary(self, last_n: int = 10) -> Dict[str, Any]:
        """Get summary of recent LLM metrics"""
        if not self.metrics_storage:
            return {"message": "No metrics available"}
            
        recent_metrics = self.metrics_storage[-last_n:] if last_n else self.metrics_storage
        
        total_calls = len(recent_metrics)
        successful_calls = len([m for m in recent_metrics if m["status"] == "success"])
        avg_latency = sum(m["latency_ms"] for m in recent_metrics) / total_calls if total_calls else 0
        
        return {
            "total_calls": total_calls,
            "successful_calls": successful_calls,
            "success_rate": successful_calls / total_calls if total_calls else 0,
            "average_latency_ms": round(avg_latency, 2),
            "recent_metrics": recent_metrics
        }

# Global instance
llm_observability = LLMObservability()

# Convenience decorators
def track_crewai_call(model: str = "crewai"):
    return llm_observability.track_llm_call(model=model, provider="crewai")
