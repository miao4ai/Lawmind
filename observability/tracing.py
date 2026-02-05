"""Distributed tracing with OpenTelemetry."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter

from shared.config import get_settings


_tracer = None


def init_tracing():
    """Initialize OpenTelemetry tracing."""
    global _tracer

    settings = get_settings()

    if not settings.enable_tracing:
        # Use no-op tracer
        trace.set_tracer_provider(TracerProvider())
        _tracer = trace.get_tracer(__name__)
        return

    # Set up Cloud Trace exporter
    tracer_provider = TracerProvider()
    cloud_trace_exporter = CloudTraceSpanExporter(
        project_id=settings.gcp_project_id
    )

    tracer_provider.add_span_processor(
        BatchSpanProcessor(cloud_trace_exporter)
    )

    trace.set_tracer_provider(tracer_provider)
    _tracer = trace.get_tracer(__name__)


def get_tracer():
    """Get tracer instance."""
    global _tracer

    if _tracer is None:
        init_tracing()

    return _tracer
