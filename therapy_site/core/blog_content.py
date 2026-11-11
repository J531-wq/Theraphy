from html import escape
from html.parser import HTMLParser
import re
from urllib.parse import urlsplit


_ALLOWED_TAGS = {
    "a", "blockquote", "br", "em", "h2", "h3", "h4", "i", "li",
    "ol", "p", "strong", "u", "ul",
}
_VOID_TAGS = {"br"}
_SKIP_CONTENT_TAGS = {"script", "style"}


class _BlogHTMLSanitizer(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.output = []
        self.open_tags = []
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if self.skip_depth:
            if tag in _SKIP_CONTENT_TAGS:
                self.skip_depth += 1
            return
        if tag in _SKIP_CONTENT_TAGS:
            self.skip_depth = 1
            return
        if tag not in _ALLOWED_TAGS:
            return

        if tag == "a":
            href = dict(attrs).get("href", "")
            if href and _is_safe_link(href):
                self.output.append(
                    f'<a href="{escape(href, quote=True)}" '
                    'rel="nofollow noopener noreferrer">'
                )
            else:
                self.output.append("<a>")
        else:
            self.output.append(f"<{tag}>")

        if tag not in _VOID_TAGS:
            self.open_tags.append(tag)

    def handle_endtag(self, tag):
        if self.skip_depth:
            if tag in _SKIP_CONTENT_TAGS:
                self.skip_depth -= 1
            return
        if tag not in self.open_tags:
            return
        while self.open_tags:
            open_tag = self.open_tags.pop()
            self.output.append(f"</{open_tag}>")
            if open_tag == tag:
                break

    def handle_data(self, data):
        if not self.skip_depth:
            self.output.append(escape(data).replace("\n", "<br>\n"))

    def sanitize(self, value):
        self.feed(value)
        self.close()
        while self.open_tags:
            self.output.append(f"</{self.open_tags.pop()}>")
        return "".join(self.output)


def _is_safe_link(href):
    parsed = urlsplit(href.strip())
    return (
        parsed.scheme.lower() in {"http", "https", "mailto"}
        or (not parsed.scheme and not parsed.netloc and href.startswith(("/", "#")))
    )


def sanitize_blog_content(value):
    content = _BlogHTMLSanitizer().sanitize(value or "")
    # Rich text editors and pasted documents often add blank paragraphs to
    # create visual spacing. They become exaggerated gaps on mobile, so keep
    # meaningful text/line breaks but discard empty spacer blocks.
    content = re.sub(r"<p>(?:\s|<br>)*</p>", "", content, flags=re.IGNORECASE)
    content = re.sub(r"<(h[2-4])>(?:\s|<br>)+", r"<\1>", content, flags=re.IGNORECASE)
    content = re.sub(r"(?:\s|<br>)+</(h[2-4])>", r"</\1>", content, flags=re.IGNORECASE)
    content = re.sub(r"(?:\s|<br>)+(</?h[2-4]>)", r"\1", content, flags=re.IGNORECASE)
    content = re.sub(r"(</h[2-4]>)(?:\s|<br>)+", r"\1", content, flags=re.IGNORECASE)
    content = re.sub(r"(?:<br>\s*){2,}", "<br>", content, flags=re.IGNORECASE)
    return content
