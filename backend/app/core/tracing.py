"""
OpenTelemetry distributed tracing configuration for AWS X-Ray.

This module configures OpenTelemetry SDK with AWS X-Ray exporter for distributed tracing
across all backend services. It provides automatic instrumentation for FastAPI, HTTP clients,
database connections, and custom spans for business logic.

Validates Requirement 18.1: Distributed tracing using OpenTelemetry
"""
import logging
from typing import Optional

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    TracerProvider = None

# Optional instrumentation packages
try:
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
except ImportError:
    HTTPXClientInstrumentor = None

try:
    from opentelemetry.instrumentation.redis import RedisInstrumentor
except ImportError:
    RedisInstrumentor = None

try:
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
except ImportError:
    SQLAlchemyInstrumentor = None

logger = logging.getLogger(__name__)


class TracingConfig:
    """OpenTelemetry tracing configuration"""
    
    def __init__(
        self,
        service_name: str,
        service_version: str,
        environment: str,
        otlp_endpoint: Optional[str] = None,
        enable_console_export: bool = False,
        sample_rate: float = 1.0,
    ):
        """
        Initialize tracing configuration.
        
        Args:
            service_name: Name of the service (e.g., "ai-code-review-api")
            service_version: Version of the service
            environment: Environment name (dev, staging, production)
            otlp_endpoint: OTLP collector endpoint (defaults to AWS X-Ray)
            enable_console_export: Enable console exporter for debugging
            sample_rate: Trace sampling rate (0.0 to 1.0)
        """
        self.service_name = service_name
        self.service_version = service_version
        self.environment = environment
        self.otlp_endpoint = otlp_endpoint or "http://localhost:4317"
        self.enable_console_export = enable_console_export
        self.sample_rate = sample_rate
        self._tracer_provider: Optional[TracerProvider] = None
        self._is_initialized = False
    
    def initialize(self) -> None:
        """Initialize OpenTelemetry tracing with AWS X-Ray exporter"""
        if self._is_initialized:
            logger.warning("Tracing already initialized, skipping")
            return
        
        try:
            # Create resource with service information
            resource = Resource.create({
                SERVICE_NAME: self.service_name,
                SERVICE_VERSION: self.service_version,
                "deployment.environment": self.environment,
            })
            
            # Create tracer provider with sampling
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
            sampler = TraceIdRatioBased(self.sample_rate)
            
            self._tracer_provider = TracerProvider(
                resource=resource,
                sampler=sampler,
            )
            
            # Configure OTLP exporter for AWS X-Ray
            otlp_exporter = OTLPSpanExporter(
                endpoint=self.otlp_endpoint,
                insecure=True,  # Use TLS in production
            )
            
            # Add batch span processor for efficient export
            span_processor = BatchSpanProcessor(otlp_exporter)
            self._tracer_provider.add_span_processor(span_processor)
            
            # Add console exporter for debugging if enabled
            if self.enable_console_export:
                from opentelemetry.sdk.trace.export import ConsoleSpanExporter
                console_exporter = ConsoleSpanExporter()
                console_processor = BatchSpanProcessor(console_exporter)
                self._tracer_provider.add_span_processor(console_processor)
            
            # Set global tracer provider
            trace.set_tracer_provider(self._tracer_provider)
            
            self._is_initialized = True
            logger.info(
                f"✅ OpenTelemetry tracing initialized: "
                f"service={self.service_name}, "
                f"environment={self.environment}, "
                f"endpoint={self.otlp_endpoint}, "
                f"sample_rate={self.sample_rate}"
            )
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenTelemetry tracing: {e}")
            raise
    
    def instrument_fastapi(self, app) -> None:
        """
        Instrument FastAPI application for automatic tracing.
        
        Args:
            app: FastAPI application instance
        """
        try:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("✅ FastAPI instrumented for tracing")
        except Exception as e:
            logger.error(f"Failed to instrument FastAPI: {e}")
    
    def instrument_httpx(self) -> None:
        """Instrument HTTPX client for automatic tracing of HTTP requests"""
        try:
            if HTTPXClientInstrumentor is None:
                logger.info("HTTPX instrumentor not available, skipping")
                return
            HTTPXClientInstrumentor().instrument()
            logger.info("✅ HTTPX instrumented for tracing")
        except Exception as e:
            logger.warning(f"HTTPX instrumentation skipped: {e}")
    
    def instrument_redis(self) -> None:
        """Instrument Redis client for automatic tracing"""
        try:
            RedisInstrumentor().instrument()
            logger.info("✅ Redis instrumented for tracing")
        except Exception as e:
            logger.error(f"Failed to instrument Redis: {e}")
    
    def instrument_sqlalchemy(self, engine) -> None:
        """
        Instrument SQLAlchemy engine for automatic tracing.
        
        Args:
            engine: SQLAlchemy engine instance
        """
        try:
            if SQLAlchemyInstrumentor is None:
                logger.info("SQLAlchemy instrumentor not available, skipping")
                return
            SQLAlchemyInstrumentor().instrument(engine=engine)
            logger.info("✅ SQLAlchemy instrumented for tracing")
        except Exception as e:
            logger.warning(f"SQLAlchemy instrumentation skipped: {e}")
    
    def get_tracer(self, name: str) -> trace.Tracer:
        """
        Get a tracer instance for creating custom spans.
        
        Args:
            name: Name of the tracer (typically module name)
            
        Returns:
            Tracer instance
        """
        return trace.get_tracer(name)
    
    def shutdown(self) -> None:
        """Shutdown tracing and flush remaining spans"""
        if self._tracer_provider:
            try:
                self._tracer_provider.shutdown()
                logger.info("✅ OpenTelemetry tracing shutdown complete")
            except Exception as e:
                logger.error(f"Error during tracing shutdown: {e}")


# Global tracing configuration instance
_tracing_config: Optional[TracingConfig] = None


def setup_tracing(
    service_name: str,
    service_version: str,
    environment: str,
    otlp_endpoint: Optional[str] = None,
    enable_console_export: bool = False,
    sample_rate: float = 1.0,
) -> TracingConfig:
    """
    Setup OpenTelemetry tracing with AWS X-Ray exporter.
    
    Args:
        service_name: Name of the service
        service_version: Version of the service
        environment: Environment name (dev, staging, production)
        otlp_endpoint: OTLP collector endpoint
        enable_console_export: Enable console exporter for debugging
        sample_rate: Trace sampling rate (0.0 to 1.0)
        
    Returns:
        TracingConfig instance
    """
    global _tracing_config
    
    if _tracing_config is not None:
        logger.warning("Tracing already configured, returning existing instance")
        return _tracing_config
    
    _tracing_config = TracingConfig(
        service_name=service_name,
        service_version=service_version,
        environment=environment,
        otlp_endpoint=otlp_endpoint,
        enable_console_export=enable_console_export,
        sample_rate=sample_rate,
    )
    
    _tracing_config.initialize()
    
    return _tracing_config


def get_tracing_config() -> Optional[TracingConfig]:
    """Get the global tracing configuration instance"""
    return _tracing_config


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance for creating custom spans.
    
    Args:
        name: Name of the tracer (typically __name__)
        
    Returns:
        Tracer instance
    """
    return trace.get_tracer(name)
