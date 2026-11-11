import logging

from django.db import DatabaseError

from .models import PageView

logger = logging.getLogger(__name__)


class PageViewMiddleware:
    """Record successful public HTML page views without storing visitor data."""

    excluded_prefixes = ("/admin/", "/admin-panel/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == "GET"
            and response.status_code < 400
            and response.get("Content-Type", "").startswith("text/html")
            and not request.path.startswith(self.excluded_prefixes)
        ):
            try:
                PageView.objects.create()
            except DatabaseError:
                logger.exception("Failed to record a public page view")
        return response
