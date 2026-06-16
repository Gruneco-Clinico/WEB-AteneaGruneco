# -*- encoding: utf-8 -*-
"""
Lightweight rate-limiting middleware for public endpoints.

Uses Django's default cache to track request counts per IP.
No external dependencies required.

Rate limit: configurable requests per window (default 30 req / 60 sec).
Applies only to specific public URL prefixes defined in RATE_LIMITED_PATHS.
"""

from django.http import JsonResponse
from django.core.cache import cache

# Public paths that need rate limiting (prefix match)
RATE_LIMITED_PATHS = [
    "/api/agendar-cita/",
    "/registro-demografico/",
    "/consulta-examenes/",
    "/guardar-examen-publico-epworth/",
    "/guardar-examen-publico-mew/",
    "/guardar-examen-publico-pitsburg/",
    "/api/disponibilidad-publica/",
]

# Limits
MAX_REQUESTS = 30  # max requests per window
WINDOW_SECONDS = 60  # window size in seconds


class RateLimitMiddleware:
    """
    Simple per-IP rate limiter for public endpoints.

    Uses Django's default cache backend (LocMemCache by default).
    For production with multiple workers, configure a shared cache
    backend (e.g., Redis or Memcached) in settings.py.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Only rate-limit specific public paths
        if not any(path.startswith(p) for p in RATE_LIMITED_PATHS):
            return self.get_response(request)

        # Get client IP (handles X-Forwarded-For from reverse proxy)
        ip = self._get_client_ip(request)
        cache_key = f"ratelimit:{ip}:{path}"

        # Check current count
        request_count = cache.get(cache_key, 0)

        if request_count >= MAX_REQUESTS:
            return JsonResponse(
                {
                    "error": "Demasiadas solicitudes. Por favor espere un momento antes de intentar nuevamente.",
                    "retry_after": WINDOW_SECONDS,
                },
                status=429,
            )

        # Increment counter
        cache.set(cache_key, request_count + 1, WINDOW_SECONDS)

        return self.get_response(request)

    @staticmethod
    def _get_client_ip(request):
        """Extract real client IP, considering reverse proxy headers."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "unknown")
