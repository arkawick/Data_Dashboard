"""
dashboard/middleware.py
=======================
Django middleware for Prometheus metrics instrumentation.

Add to MIDDLEWARE in settings.py (after SecurityMiddleware):
    'dashboard.middleware.PrometheusMiddleware',
"""

import time
from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "django_requests_total",
    "Total Django HTTP requests",
    ["method", "view", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "django_request_seconds",
    "Django request latency in seconds",
    ["method", "view"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)


class PrometheusMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.time()
        response = self.get_response(request)
        elapsed = time.time() - start

        # Resolve view name (best effort)
        view_name = "unknown"
        if hasattr(request, "resolver_match") and request.resolver_match:
            view_name = request.resolver_match.view_name or "unknown"

        method = request.method
        status = str(response.status_code)

        REQUEST_COUNT.labels(
            method=method,
            view=view_name,
            status_code=status,
        ).inc()
        REQUEST_LATENCY.labels(method=method, view=view_name).observe(elapsed)

        return response
