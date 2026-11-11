from django import template
from django.utils.safestring import mark_safe

from core.blog_content import sanitize_blog_content

register = template.Library()


@register.filter
def safe_blog_content(value):
    return mark_safe(sanitize_blog_content(value))
