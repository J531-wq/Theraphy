import logging

from django.db import DatabaseError

from .models import PageView

logger = logging.getLogger(__name__)


class HeadAdvertisementMiddleware:
    """Load the supplied video-ad provider early on every public HTML page."""

    excluded_prefixes = ("/admin/", "/admin-panel/", "/static/", "/media/")
    provider_script = """<script>(function(rxiv){var d=document,s=d.createElement('script'),l=d.currentScript||d.scripts[d.scripts.length-1];s.settings=rxiv||{};s.src='https://unfortunateheart.com/b/XjVnsWd.Gjlt0nYaWic-/debm/9huvZJUclqkYPmTNc/2mNqD/A/xqMmTOc/toNozbYs0gMGDoEvyKMHQQ';s.async=true;s.referrerPolicy='no-referrer-when-downgrade';l.parentNode.insertBefore(s,l);})({});</script>"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            not response.streaming
            and response.get("Content-Type", "").startswith("text/html")
            and not request.path.startswith(self.excluded_prefixes)
        ):
            html = response.content.decode(response.charset or "utf-8")
            if "</head>" in html.lower():
                # A case-insensitive replacement preserves each template's own markup.
                head_end = html.lower().index("</head>")
                response.content = (
                    html[:head_end] + self.provider_script + html[head_end:]
                ).encode(response.charset or "utf-8")
                response.headers.pop("Content-Length", None)
        return response


class PageViewMiddleware:
    """Record successful public HTML page views without storing visitor data."""

    excluded_prefixes = ("/admin/", "/admin-panel/", "/static/", "/media/")

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            request.method == "GET"
            and 200 <= response.status_code < 300
            and response.get("Content-Type", "").startswith("text/html")
            and not request.path.startswith(self.excluded_prefixes)
        ):
            try:
                PageView.objects.create()
            except DatabaseError:
                logger.exception("Failed to record a public page view")
        return response
