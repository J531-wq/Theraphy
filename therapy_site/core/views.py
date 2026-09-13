import hashlib
import logging
import random

from django.contrib.auth.hashers import check_password, make_password
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.db.models import F
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import (
    ForgotPasswordForm,
    LoginForm,
    RegisterForm,
    ResetPasswordForm,
    VerificationCodeForm,
)
from .models import (
    Blog,
    BlogComment,
    BlogCommentVote,
    BlogPostLike,
    BlogSubscriber,
    ChatMessage,
    ChatSession,
    User,
)
from .services.email_service import (
    send_blog_subscription_welcome,
    send_reset_email,
    send_verification_email,
    send_welcome_email,
)
from .services.groq_client import get_ai_response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_chat_user(request):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def _get_or_create_session(request, user, section):
    """
    Return the active ChatSession for this user+section from the Django
    session.  Creates a new DB row if none exists yet.
    """
    key = f"chat_session_{section}"
    session_id = request.session.get(key)

    if session_id:
        try:
            return ChatSession.objects.get(id=session_id, user=user, section=section)
        except ChatSession.DoesNotExist:
            pass  # stale id — create a fresh one

    chat_session = ChatSession.objects.create(
        user=user,
        section=section,
        title="New Conversation",
    )
    request.session[key] = chat_session.id
    request.session.modified = True
    return chat_session


def _section_history(user, chat_session):
    """Return all messages for a given ChatSession ordered oldest-first."""
    return ChatMessage.objects.filter(
        user=user,
        session=chat_session,
    ).order_by("created_at")


def _all_sessions(user, section):
    """Return all ChatSessions for a user+section, newest first."""
    return ChatSession.objects.filter(
        user=user,
        section=section,
    ).order_by("-created_at")


# ---------------------------------------------------------------------------
# Shared therapy chat handler
# ---------------------------------------------------------------------------

# Maps section slug → (template, therapist_name)
SECTION_META = {
    "child":        ("core/child.html",        "Daniel Carter"),
    "teen":         ("core/teen.html",          "Emily Parker"),
    "trauma":       ("core/trauma.html",        "Michael Bennett"),
    "addiction":    ("core/addiction.html",     "James Anderson"),
    "family":       ("core/family.html",        "Sophia Williams"),
    "relationship": ("core/relationship.html",  "Ethan Thompson"),
    "stress":       ("core/stress.html",        "AI Assistant"),
    "general":      ("core/stress.html",        "AI Assistant"),
}


def therapy_section(request, section):
    user = get_chat_user(request)

    # ── Login required ─────────────────────────────────────────────────────
    if not user:
        login_url = f"{reverse('login')}?next={request.path}"
        if request.method == "POST":
            return JsonResponse(
                {"error": "Please sign in to continue.", "redirect": login_url},
                status=401,
            )
        return redirect(login_url)

    # ── POST — send a message ──────────────────────────────────────────────
    if request.method == "POST":
        # New chat action
        if request.POST.get("action") == "new_chat":
            if user:
                key = f"chat_session_{section}"
                request.session.pop(key, None)
                request.session.modified = True
            return JsonResponse({"status": "ok"})

        user_message = request.POST.get("message", "").strip()
        if not user_message:
            return JsonResponse({"error": "Please enter a message."}, status=400)

        # Build conversation history for context-aware sections
        history = []
        chat_session = None

        if user:
            chat_session = _get_or_create_session(request, user, section)
            prev = _section_history(user, chat_session)
            history = [{"role": m.role, "content": m.content} for m in prev]

        try:
            reply = get_ai_response(section, user_message, history=history)
        except Exception as exc:
            logger.error("Groq error in section=%s: %s", section, exc, exc_info=True)
            return JsonResponse(
                {"error": f"AI error: {exc}"},
                status=500,
            )

        # Persist messages
        if user and chat_session:
            # Auto-title the session from the first user message
            if not _section_history(user, chat_session).exists():
                chat_session.title = user_message[:80]
                chat_session.save(update_fields=["title"])

            ChatMessage.objects.create(
                user=user, session=chat_session,
                section=section, role="user", content=user_message,
            )
            ChatMessage.objects.create(
                user=user, session=chat_session,
                section=section, role="assistant", content=reply,
            )

        return JsonResponse({"reply": reply})

    # ── GET — render the chat page ─────────────────────────────────────────
    template, _ = SECTION_META.get(section, (f"core/{section}.html", ""))

    chat_session = None
    chat_history = []
    all_sessions = []

    if user:
        chat_session = _get_or_create_session(request, user, section)
        chat_history = list(_section_history(user, chat_session))
        all_sessions = list(_all_sessions(user, section))

    return render(request, template, {
        "chat_history":  chat_history,
        "all_sessions":  all_sessions,
        "chat_session":  chat_session,
        "section":       section,
    })


# Switch session — load an existing past session
def switch_session(request, section, session_id):
    user = get_chat_user(request)
    if not user:
        return redirect("login")

    try:
        ChatSession.objects.get(id=session_id, user=user, section=section)
        key = f"chat_session_{section}"
        request.session[key] = session_id
        request.session.modified = True
    except ChatSession.DoesNotExist:
        pass

    return redirect("therapy_section", section=section)


# ---------------------------------------------------------------------------
# Legacy per-section views (kept so old URLs still work)
# ---------------------------------------------------------------------------

def child_therapy(request):
    return therapy_section(request, "child")

def teen_therapy(request):
    return therapy_section(request, "teen")

def trauma_therapy(request):
    return therapy_section(request, "trauma")

def addiction_therapy(request):
    return therapy_section(request, "addiction")

def family_therapy(request):
    return therapy_section(request, "family")

def relationship_therapy(request):
    return therapy_section(request, "relationship")

def general_ai_search(request):
    return therapy_section(request, "stress")


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def welcome(request):
    return render(request, "core/welcome.html", {
        "total_users":  User.objects.count(),
        "active_users": User.objects.filter(is_active=True).count(),
    })


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            verification_code = str(random.randint(100000, 999999))
            user.save()
            request.session["verification_code"] = verification_code
            request.session["verification_username"] = user.username
            user.verification_code = verification_code
            sent = send_verification_email(user)
            if not sent:
                user.delete()
                return render(request, "core/register.html", {
                    "form": form,
                    "error": (
                        "We could not send the verification email. "
                        "Please check your email address and try again."
                    ),
                })
            return redirect("verify_email")
    else:
        form = RegisterForm()
    return render(request, "core/register.html", {"form": form})


def verify_email(request):
    username   = request.session.get("verification_username")
    saved_code = request.session.get("verification_code")
    if not username or not saved_code:
        return redirect("register")
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect("register")

    if request.method == "POST":
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["verification_code"] == saved_code:
                user.is_active = True
                user.save()
                request.session["user_id"] = user.id
                request.session.pop("verification_code", None)
                request.session.pop("verification_username", None)
                send_welcome_email(user)
                return redirect("sections")
            return render(request, "core/verify_email.html", {
                "form": form,
                "error": "Invalid verification code.",
                "email": user.email,
            })
    else:
        form = VerificationCodeForm()
    return render(request, "core/verify_email.html", {"form": form, "email": user.email})


def login_view(request):
    next_url = request.GET.get("next") or request.POST.get("next") or "sections"
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]
            try:
                user = User.objects.get(username=username)
                if not user.is_active:
                    return render(request, "core/login.html", {
                        "form": form,
                        "error": "Please verify your email before logging in.",
                        "next": next_url,
                    })
                if check_password(password, user.password):
                    request.session["user_id"] = user.id
                    request.session.modified = True
                    return redirect(next_url)
                return render(request, "core/login.html", {
                    "form": form, "error": "Incorrect password.",
                    "next": next_url,
                })
            except User.DoesNotExist:
                return render(request, "core/login.html", {
                    "form": form,
                    "error": "Invalid credentials. Kindly register an account.",
                    "next": next_url,
                })
    else:
        form = LoginForm()
    return render(request, "core/login.html", {"form": form, "next": next_url})


def forgot_password(request):
    if request.method == "POST":
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(username=form.cleaned_data["username"])
                verification_code = str(random.randint(100000, 999999))
                if not send_reset_email(user, verification_code):
                    return render(request, "core/forgot_password.html", {
                        "form": form,
                        "error": "We could not send the recovery email. Please try again later.",
                    })
                request.session["reset_username"] = user.username
                request.session["reset_code"] = verification_code
                return redirect("verify_reset_code")
            except User.DoesNotExist:
                return render(request, "core/forgot_password.html", {
                    "form": form, "error": "User not found.",
                })
    else:
        form = ForgotPasswordForm()
    return render(request, "core/forgot_password.html", {"form": form})


def verify_reset_code(request):
    username   = request.session.get("reset_username")
    saved_code = request.session.get("reset_code")
    if not username or not saved_code:
        return redirect("login")
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect("login")

    if request.method == "POST":
        form = VerificationCodeForm(request.POST)
        if form.is_valid():
            if form.cleaned_data["verification_code"] == saved_code:
                request.session["password_reset_username"] = username
                request.session.pop("reset_code", None)
                request.session.pop("reset_username", None)
                return redirect("reset_password")
            return render(request, "core/verify_reset_code.html", {
                "form": form,
                "error": "Invalid verification code.",
                "email": user.email,
            })
    else:
        form = VerificationCodeForm()
    return render(request, "core/verify_reset_code.html", {"form": form, "email": user.email})


def reset_password(request):
    username = request.session.get("password_reset_username")
    if not username:
        return redirect("login")
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect("login")

    if request.method == "POST":
        form = ResetPasswordForm(request.POST)
        if form.is_valid():
            new_username = form.cleaned_data.get("username")
            password     = form.cleaned_data.get("password")
            if not new_username:
                return render(request, "core/reset_password.html", {
                    "form": form, "error": "Please enter a new username.",
                })
            if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                return render(request, "core/reset_password.html", {
                    "form": form,
                    "error": "That username is already taken. Please choose another.",
                })
            user.username = new_username
            user.password = make_password(password)
            user.is_active = True
            user.save()
            request.session.pop("password_reset_username", None)
            return redirect("login")
    else:
        form = ResetPasswordForm()
    return render(request, "core/reset_password.html", {"form": form})


def sections(request):
    return render(request, "core/sections.html")


def logout_view(request):
    request.session.flush()
    return redirect("welcome")


def reset_users(request):
    User.objects.filter(is_superuser=False).delete()
    return redirect("welcome")


# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------

def error_400(request, exception=None):
    return render(request, "core/400.html", status=400)

def error_403(request, exception=None):
    return render(request, "core/403.html", status=403)

def error_404(request, exception=None):
    return render(request, "core/404.html", status=404)

def error_500(request):
    return render(request, "core/500.html", status=500)


# ---------------------------------------------------------------------------
# SEO endpoints (robots.txt + sitemap.xml)
# ---------------------------------------------------------------------------

BASE_URL = "https://mytherapydoctor.com"


def robots_txt(request):
    """Serve a standard robots.txt that points crawlers to the sitemap."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Disallow: /admin/\n"
        "Disallow: /login/\n"
        "Disallow: /register/\n"
        "Disallow: /verify-email/\n"
        "Disallow: /forgot-password/\n"
        "Disallow: /verify-reset-code/\n"
        "Disallow: /reset-password/\n"
        "Disallow: /reset/\n"
        f"Sitemap: {BASE_URL}/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


def sitemap_xml(request):
    """Generate an XML sitemap of all public, indexable pages."""
    static_pages = [
        ("/", "1.0", "daily"),
        ("/sections/", "0.9", "weekly"),
        ("/blog/", "0.9", "daily"),
        ("/blog/feed/", "0.7", "daily"),
        ("/therapy/child/", "0.8", "weekly"),
        ("/therapy/teen/", "0.8", "weekly"),
        ("/therapy/trauma/", "0.8", "weekly"),
        ("/therapy/addiction/", "0.8", "weekly"),
        ("/therapy/family/", "0.8", "weekly"),
        ("/therapy/relationship/", "0.8", "weekly"),
        ("/therapy/general/", "0.8", "weekly"),
    ]
    # Every published blog post — keeps Google discovering new content fast.
    blog_entries = []
    for post in Blog.objects.filter(is_published=True).order_by('-updated_at'):
        lastmod = post.updated_at.strftime('%Y-%m-%d')
        blog_entries.append(
            f"  <url>\n"
            f"    <loc>{BASE_URL}{post.get_absolute_url()}</loc>\n"
            f"    <lastmod>{lastmod}</lastmod>\n"
            f"    <changefreq>weekly</changefreq>\n"
            f"    <priority>0.8</priority>\n"
            f"  </url>"
        )
    entries = [
        f"  <url>\n"
        f"    <loc>{BASE_URL}{path}</loc>\n"
        f"    <changefreq>{freq}</changefreq>\n"
        f"    <priority>{prio}</priority>\n"
        f"  </url>"
        for path, prio, freq in static_pages
    ] + blog_entries
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "\n".join(entries) +
        '\n</urlset>\n'
    )
    return HttpResponse(xml, content_type="application/xml")


# ---------------------------------------------------------------------------
# Blog views
# ---------------------------------------------------------------------------

def _voter_key(request):
    """
    Stable anonymous voter id: logged-in user id if present, else the
    Django session key (created on demand).  Hashed so raw ids never
    touch the database.
    """
    user_id = request.session.get("user_id")
    if user_id:
        raw = f"user:{user_id}"
    else:
        if not request.session.session_key:
            request.session.save()
        raw = f"session:{request.session.session_key or 'anon'}"
    return hashlib.sha256(raw.encode()).hexdigest()


def blog_list(request):
    """Display all published blog posts, 21 per page."""
    category = request.GET.get('category', None)

    # Get published blogs
    blogs = Blog.objects.filter(is_published=True).order_by('-created_at')

    # Filter by category if provided
    if category:
        blogs = blogs.filter(category=category)

    paginator = Paginator(blogs, 21)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all categories for filter pills
    categories = Blog.CATEGORY_CHOICES

    context = {
        'blogs': page_obj.object_list,
        'page_obj': page_obj,
        'categories': categories,
        'selected_category': category,
        'total_blogs': paginator.count,
    }

    return render(request, 'core/blog_list.html', context)


def blog_detail(request, slug):
    """Display a single blog post in detail."""
    try:
        blog = Blog.objects.get(slug=slug, is_published=True)
    except Blog.DoesNotExist:
        return render(request, 'core/404.html', status=404)

    # Get related blogs (same category)
    related_blogs = Blog.objects.filter(
        category=blog.category,
        is_published=True
    ).exclude(id=blog.id).order_by('-created_at')[:3]

    # Top-level approved comments + their approved replies
    top_comments = (
        BlogComment.objects
        .filter(post=blog, parent__isnull=True, is_approved=True)
        .prefetch_related('replies')
        .order_by('created_at')
    )
    comments = []
    for comment in top_comments:
        replies = [r for r in comment.replies.all() if r.is_approved]
        comments.append({'comment': comment, 'replies': replies})

    # Has this visitor already liked the post?
    post_liked = BlogPostLike.objects.filter(
        post=blog, voter_key=_voter_key(request)
    ).exists()

    context = {
        'blog': blog,
        'related_blogs': related_blogs,
        'comments': comments,
        'comment_count': top_comments.count(),
        'post_liked': post_liked,
        'current_user': get_chat_user(request),
    }

    return render(request, 'core/blog_detail.html', context)


@require_POST
def blog_subscribe(request):
    """AJAX subscribe endpoint — stores the email, sends a ZeptoMail welcome."""
    email = request.POST.get('email', '').strip().lower()
    name = request.POST.get('name', '').strip()[:100]
    if not email or '@' not in email or '.' not in email.split('@')[-1]:
        return JsonResponse(
            {'ok': False, 'message': 'Please enter a valid email address.'},
            status=400,
        )
    subscriber, created = BlogSubscriber.objects.get_or_create(
        email=email, defaults={'name': name}
    )
    if not created and not subscriber.is_active:
        subscriber.is_active = True
        subscriber.save(update_fields=['is_active'])
    absolute = request.build_absolute_uri('/').rstrip('/')
    unsubscribe_url = f"{absolute}/blog/unsubscribe/{subscriber.token}/"
    send_blog_subscription_welcome(
        email, name or subscriber.name, unsubscribe_url
    )
    return JsonResponse(
        {'ok': True, 'message': 'Thanks for subscribing! Please check your inbox.'}
    )


def blog_unsubscribe(request, token):
    """One-click unsubscribe link from notification emails."""
    subscriber = get_object_or_404(BlogSubscriber, token=token)
    subscriber.is_active = False
    subscriber.save(update_fields=['is_active'])
    return render(
        request, 'core/blog_unsubscribe.html', {'email': subscriber.email}
    )


@require_POST
def blog_comment_create(request, slug):
    """AJAX endpoint — post a comment or one-level reply."""
    blog = get_object_or_404(Blog, slug=slug, is_published=True)
    user = get_chat_user(request)
    name = request.POST.get('name', '').strip()[:100]
    body = request.POST.get('body', '').strip()
    parent_id = request.POST.get('parent_id')
    if not body or (not user and not name):
        return JsonResponse(
            {'ok': False, 'message': 'Please enter your name and comment.' if not user else 'Please enter a comment.'},
            status=400,
        )
    if len(body) > 2000:
        return JsonResponse(
            {'ok': False, 'message': 'Comment is too long (max 2000 characters).'},
            status=400,
        )
    parent = None
    if parent_id:
        parent = get_object_or_404(
            BlogComment, id=parent_id, post=blog, is_approved=True
        )
        if parent.parent_id is not None:
            # Replies nest only one level — reply to the top-level parent.
            parent = parent.parent
    comment = BlogComment.objects.create(
        post=blog, parent=parent, owner=user,
        name=(user.full_name or user.username) if user else name,
        email=user.email if user and user.email else '',
        body=body,
    )
    return JsonResponse({
        'ok': True,
        'comment': {
            'id': comment.id,
            'name': comment.name,
            'body': comment.body,
            'created': timezone.localtime(comment.created_at).strftime('%b %d, %Y'),
            'parent_id': parent.id if parent else None,
            'is_owner': bool(user and comment.owner_id == user.id),
        },
    })


@require_POST
def blog_comment_edit(request, comment_id):
    comment = get_object_or_404(BlogComment, id=comment_id, is_approved=True)
    user = get_chat_user(request)
    if not user or comment.owner_id != user.id:
        return JsonResponse({'ok': False, 'message': 'You can only edit your own comments.'}, status=403)
    body = request.POST.get('body', '').strip()
    if not body or len(body) > 2000:
        return JsonResponse({'ok': False, 'message': 'Comment must contain 1 to 2000 characters.'}, status=400)
    comment.body = body
    comment.save(update_fields=['body'])
    return JsonResponse({'ok': True, 'body': comment.body})


@require_POST
def blog_comment_delete(request, comment_id):
    comment = get_object_or_404(BlogComment, id=comment_id, is_approved=True)
    user = get_chat_user(request)
    if not user or comment.owner_id != user.id:
        return JsonResponse({'ok': False, 'message': 'You can only delete your own comments.'}, status=403)
    comment.delete()
    return JsonResponse({'ok': True})


@require_POST
def blog_comment_vote(request, comment_id):
    """AJAX endpoint — like or dislike a comment (one vote per visitor)."""
    comment = get_object_or_404(BlogComment, id=comment_id, is_approved=True)
    try:
        value = int(request.POST.get('value', 0))
    except (TypeError, ValueError):
        value = 0
    if value not in (BlogCommentVote.LIKE, BlogCommentVote.DISLIKE):
        return JsonResponse(
            {'ok': False, 'message': 'Invalid vote.'}, status=400
        )
    key = _voter_key(request)
    existing = BlogCommentVote.objects.filter(
        comment=comment, voter_key=key
    ).first()
    if existing and existing.value == value:
        # Toggle off — remove the vote.
        existing.delete()
        if value == BlogCommentVote.LIKE:
            BlogComment.objects.filter(id=comment.id).update(
                likes_count=F('likes_count') - 1
            )
        else:
            BlogComment.objects.filter(id=comment.id).update(
                dislikes_count=F('dislikes_count') - 1
            )
        user_vote = 0
    elif existing:
        # Switch sides.
        existing.value = value
        existing.save(update_fields=['value'])
        if value == BlogCommentVote.LIKE:
            BlogComment.objects.filter(id=comment.id).update(
                likes_count=F('likes_count') + 1,
                dislikes_count=F('dislikes_count') - 1,
            )
        else:
            BlogComment.objects.filter(id=comment.id).update(
                likes_count=F('likes_count') - 1,
                dislikes_count=F('dislikes_count') + 1,
            )
        user_vote = value
    else:
        try:
            BlogCommentVote.objects.create(
                comment=comment, voter_key=key, value=value
            )
        except IntegrityError:
            pass
        if value == BlogCommentVote.LIKE:
            BlogComment.objects.filter(id=comment.id).update(
                likes_count=F('likes_count') + 1
            )
        else:
            BlogComment.objects.filter(id=comment.id).update(
                dislikes_count=F('dislikes_count') + 1
            )
        user_vote = value
    # Guard against negative counters from legacy rows.
    BlogComment.objects.filter(
        id=comment.id, likes_count__lt=0
    ).update(likes_count=0)
    BlogComment.objects.filter(
        id=comment.id, dislikes_count__lt=0
    ).update(dislikes_count=0)
    comment.refresh_from_db()
    return JsonResponse({
        'ok': True,
        'likes': comment.likes_count,
        'dislikes': comment.dislikes_count,
        'user_vote': user_vote,
    })


@require_POST
def blog_post_like(request, slug):
    """AJAX endpoint — toggle this visitor's like on a post."""
    blog = get_object_or_404(Blog, slug=slug, is_published=True)
    key = _voter_key(request)
    existing = BlogPostLike.objects.filter(post=blog, voter_key=key).first()
    if existing:
        existing.delete()
        Blog.objects.filter(id=blog.id).update(
            likes_count=F('likes_count') - 1
        )
        liked = False
    else:
        try:
            BlogPostLike.objects.create(post=blog, voter_key=key)
        except IntegrityError:
            pass
        Blog.objects.filter(id=blog.id).update(
            likes_count=F('likes_count') + 1
        )
        liked = True
    Blog.objects.filter(id=blog.id, likes_count__lt=0).update(likes_count=0)
    blog.refresh_from_db()
    return JsonResponse({'ok': True, 'likes': blog.likes_count, 'liked': liked})


def blog_feed(request):
    """RSS 2.0 feed of the latest published posts (fast Google indexing)."""
    posts = Blog.objects.filter(is_published=True).order_by('-created_at')[:20]
    base = request.build_absolute_uri('/').rstrip('/')
    xml_items = []
    for post in posts:
        image_url = ''
        if post.featured_image:
            try:
                image_url = f"{base}{post.featured_image.url}"
            except ValueError:
                image_url = ''
        image_url = image_url or (post.cover_image_url or '')
        enclosure = (
            f'\n      <enclosure url="{image_url}" type="image/jpeg" />'
            if image_url else ''
        )
        pub_date = post.created_at.strftime('%a, %d %b %Y %H:%M:%S +0000')
        xml_items.append(
            f"    <item>\n"
            f"      <title>{post.title}</title>\n"
            f"      <link>{base}{post.get_absolute_url()}</link>\n"
            f"      <guid isPermaLink=\"true\">{base}{post.get_absolute_url()}</guid>\n"
            f"      <description>{post.excerpt}</description>\n"
            f"      <pubDate>{pub_date}</pubDate>\n"
            f"      <author>{post.author}</author>\n"
            f"      <category>{post.get_category_display()}</category>{enclosure}\n"
            f"    </item>"
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0">\n'
        '  <channel>\n'
        '    <title>MyTherapyDoctor Blog</title>\n'
        f'    <link>{base}/blog/</link>\n'
        '    <description>Mental health insights, wellness tips and therapy advice.</description>\n'
        '    <language>en-us</language>\n'
        + '\n'.join(xml_items) +
        '\n  </channel>\n'
        '</rss>\n'
    )
    return HttpResponse(xml, content_type="application/rss+xml")
