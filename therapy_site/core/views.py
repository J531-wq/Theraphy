import logging
import random

from django.contrib.auth.hashers import check_password, make_password
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import (
    ForgotPasswordForm,
    LoginForm,
    RegisterForm,
    ResetPasswordForm,
    VerificationCodeForm,
)
from .models import ChatMessage, ChatSession, User
from .services.email_service import (
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
                    })
                if check_password(password, user.password):
                    request.session["user_id"] = user.id
                    request.session.modified = True
                    return redirect("sections")
                return render(request, "core/login.html", {
                    "form": form, "error": "Incorrect password.",
                })
            except User.DoesNotExist:
                return render(request, "core/login.html", {
                    "form": form,
                    "error": "Invalid credentials. Kindly register an account.",
                })
    else:
        form = LoginForm()
    return render(request, "core/login.html", {"form": form})


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
