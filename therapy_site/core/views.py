from django.shortcuts import render, redirect
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.conf import settings
from .models import User, ChatMessage
from .forms import (
    RegisterForm,
    LoginForm,
    ForgotPasswordForm,
    VerificationCodeForm,
    ResetPasswordForm
)

import random

# core/views.py
from django.shortcuts import render
from django.http import JsonResponse
from core.services.groq_client import get_ai_response


def get_chat_user(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None


def get_chat_history(user, section):
    if not user:
        return []

    messages = ChatMessage.objects.filter(
        user=user,
        section=section
    ).order_by("created_at")

    return messages


def child_therapy(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message")

        reply = get_ai_response("child", user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section="child",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="child",
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "child")

    return render(
        request,
        "core/child.html",
        {"chat_history": chat_history}
    )


def teen_therapy(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message")

        reply = get_ai_response("teen", user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section="teen",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="teen",
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "teen")

    return render(
        request,
        "core/teen.html",
        {"chat_history": chat_history}
    )


def trauma_therapy(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message")

        reply = get_ai_response("trauma", user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section="trauma",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="trauma",
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "trauma")

    return render(
        request,
        "core/trauma.html",
        {"chat_history": chat_history}
    )


def general_ai_search(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if not user_message:
            return JsonResponse(
                {"reply": "Please enter a message."},
                status=400
            )

        # Get General AI conversation history from the database
        history = []

        if user:
            previous_messages = ChatMessage.objects.filter(
                user=user,
                section="general"
            ).order_by("-created_at")[:20]

            previous_messages = list(reversed(previous_messages))

            for chat_message in previous_messages:
                history.append({
                    "role": chat_message.role,
                    "content": chat_message.content
                })

        # If there is no database history yet, keep the existing
        # session-based history as a fallback.
        if not history:
            history = request.session.get(
                "general_ai_history",
                []
            )

            if not isinstance(history, list):
                history = []

        # Send the previous conversation together with
        # the new message so the AI can understand follow-up questions.
        reply = get_ai_response(
            "general",
            user_message,
            history=history
        )

        # Save the conversation to the database
        if user:
            ChatMessage.objects.create(
                user=user,
                section="general",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="general",
                role="assistant",
                content=reply
            )

        # Keep the existing session history as well
        history.append({
            "role": "user",
            "content": user_message
        })

        history.append({
            "role": "assistant",
            "content": reply
        })

        # Keep the latest 20 messages for conversation context
        request.session["general_ai_history"] = history[-20:]

        # Make sure Django saves the updated session
        request.session.modified = True

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "general")

    return render(
        request,
        "core/general.html",
        {"chat_history": chat_history}
    )


def addiction_therapy(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message")

        reply = get_ai_response("addiction", user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section="addiction",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="addiction",
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "addiction")

    return render(
        request,
        "core/addiction.html",
        {"chat_history": chat_history}
    )


def family_therapy(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message")

        reply = get_ai_response("family", user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section="family",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="family",
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "family")

    return render(
        request,
        "core/family.html",
        {"chat_history": chat_history}
    )


def relationship_therapy(request):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message")

        reply = get_ai_response("relationship", user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section="relationship",
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section="relationship",
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, "relationship")

    return render(
        request,
        "core/relationship.html",
        {"chat_history": chat_history}
    )


def welcome(request):
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()

    return render(request, 'core/welcome.html', {
        'total_users': total_users,
        'active_users': active_users
    })


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save(commit=False)

            # New account must remain inactive until email is verified
            user.is_active = False

            # Generate 6-digit verification code
            verification_code = str(random.randint(100000, 999999))

            # Save user information temporarily in the session
            request.session['verification_code'] = verification_code
            request.session['verification_username'] = user.username

            # Save the user first
            user.save()

            # Send verification code to the registered email
            send_mail(
                subject='Therapy Portal - Email Verification Code',
                message=(
                    f'Hello {user.full_name},\n\n'
                    f'Your Therapy Portal verification code is: '
                    f'{verification_code}\n\n'
                    f'Enter this code on the verification page to confirm '
                    f'your email address.\n\n'
                    f'If you did not create this account, please ignore this email.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

            return redirect('verify_email')

    else:
        form = RegisterForm()

    return render(request, 'core/register.html', {'form': form})


def verify_email(request):
    username = request.session.get('verification_username')
    saved_code = request.session.get('verification_code')

    if not username or not saved_code:
        return redirect('register')

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('register')

    if request.method == 'POST':

        form = VerificationCodeForm(request.POST)

        if form.is_valid():

            entered_code = form.cleaned_data['verification_code']

            if entered_code == saved_code:

                user.is_active = True
                user.save()

                # Keep the verified user identified in the session
                request.session['user_id'] = user.id

                # Remove verification information from session
                request.session.pop('verification_code', None)
                request.session.pop('verification_username', None)

                return redirect('sections')

            else:
                return render(request, 'core/verify_email.html', {
                    'form': form,
                    'error': 'Invalid verification code.',
                    'email': user.email
                })

    else:
        form = VerificationCodeForm()

    return render(request, 'core/verify_email.html', {
        'form': form,
        'email': user.email
    })


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request.POST)

        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']

            try:
                user = User.objects.get(username=username)

                # Do not allow login until email has been verified
                if not user.is_active:
                    return render(request, 'core/login.html', {
                        'form': form,
                        'error': 'Please verify your email before logging in.'
                    })

                # Check the entered password against the stored hashed password
                if check_password(password, user.password):
                    user.is_active = True
                    user.save()

                    # Remember which user is logged in
                    request.session['user_id'] = user.id
                    request.session.modified = True

                    return redirect('sections')

                else:
                    return render(request, 'core/login.html', {
                        'form': form,
                        'error': 'Incorrect password.'
                    })

            except User.DoesNotExist:
                return render(request, 'core/login.html', {
                    'form': form,
                    'error': 'Invalid credentials. Kindly register an account.'
                })

    else:
        form = LoginForm()

    return render(request, 'core/login.html', {'form': form})


def forgot_password(request):
    """
    Start the password/username recovery process.

    The username is used to identify the account.
    The registered email belonging to that account is then
    retrieved automatically and used to send the verification code.
    """

    if request.method == 'POST':

        form = ForgotPasswordForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data['username']

            try:
                user = User.objects.get(username=username)

                # Generate 6-digit password/username reset code
                verification_code = str(
                    random.randint(100000, 999999)
                )

                # Store recovery information in session
                request.session['reset_username'] = user.username
                request.session['reset_code'] = verification_code

                # Send code automatically to the registered email
                send_mail(
                    subject='Therapy Portal - Account Recovery Code',
                    message=(
                        f'Hello {user.full_name},\n\n'
                        f'Your Therapy Portal account recovery verification '
                        f'code is: {verification_code}\n\n'
                        f'Enter this code on the verification page to '
                        f'continue recovering your account.\n\n'
                        f'If you did not request account recovery, '
                        f'please ignore this email.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )

                return redirect('verify_reset_code')

            except User.DoesNotExist:
                return render(request, 'core/forgot_password.html', {
                    'form': form,
                    'error': 'User not found.'
                })

    else:
        form = ForgotPasswordForm()

    return render(request, 'core/forgot_password.html', {
        'form': form
    })


def verify_reset_code(request):
    username = request.session.get('reset_username')
    saved_code = request.session.get('reset_code')

    if not username or not saved_code:
        return redirect('login')

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':

        form = VerificationCodeForm(request.POST)

        if form.is_valid():

            entered_code = form.cleaned_data['verification_code']

            if entered_code == saved_code:

                # Keep the current username temporarily
                # until the new username is saved.
                request.session['password_reset_username'] = username

                # Remove the verification code after successful verification
                request.session.pop('reset_code', None)
                request.session.pop('reset_username', None)

                return redirect('reset_password')

            else:
                return render(request, 'core/verify_reset_code.html', {
                    'form': form,
                    'error': 'Invalid verification code.',
                    'email': user.email
                })

    else:
        form = VerificationCodeForm()

    return render(request, 'core/verify_reset_code.html', {
        'form': form,
        'email': user.email
    })


def reset_password(request):
    username = request.session.get('password_reset_username')

    if not username:
        return redirect('login')

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return redirect('login')

    if request.method == 'POST':

        form = ResetPasswordForm(request.POST)

        if form.is_valid():

            new_username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')

            # Make sure a new username was supplied
            if not new_username:
                return render(request, 'core/reset_password.html', {
                    'form': form,
                    'error': 'Please enter a new username.'
                })

            # Check whether another account already uses the new username
            username_exists = User.objects.filter(
                username=new_username
            ).exclude(
                pk=user.pk
            ).exists()

            if username_exists:
                return render(request, 'core/reset_password.html', {
                    'form': form,
                    'error': 'That username is already taken. Please choose another username.'
                })

            # Update BOTH username and password
            user.username = new_username
            user.password = make_password(password)
            user.is_active = True
            user.save()

            # Remove password/username reset information
            request.session.pop('password_reset_username', None)

            # Send the user back to login with the new credentials
            return redirect('login')

    else:
        form = ResetPasswordForm()

    return render(request, 'core/reset_password.html', {
        'form': form
    })


def sections(request):
    return render(request, 'core/sections.html')


def therapy_section(request, section):
    user = get_chat_user(request)

    if request.method == "POST":
        user_message = request.POST.get("message", "").strip()

        if not user_message:
            return JsonResponse(
                {"reply": "Please enter a message."},
                status=400
            )

        # General AI needs conversation history.
        # This also handles the case where general.html
        # sends its request through the generic therapy_section URL.
        if section == "general":

            history = []

            if user:
                previous_messages = ChatMessage.objects.filter(
                    user=user,
                    section="general"
                ).order_by("-created_at")[:20]

                previous_messages = list(reversed(previous_messages))

                for chat_message in previous_messages:
                    history.append({
                        "role": chat_message.role,
                        "content": chat_message.content
                    })

            if not history:
                history = request.session.get(
                    "general_ai_history",
                    []
                )

                if not isinstance(history, list):
                    history = []

            reply = get_ai_response(
                "general",
                user_message,
                history=history
            )

            if user:
                ChatMessage.objects.create(
                    user=user,
                    section="general",
                    role="user",
                    content=user_message
                )

                ChatMessage.objects.create(
                    user=user,
                    section="general",
                    role="assistant",
                    content=reply
                )

            history.append({
                "role": "user",
                "content": user_message
            })

            history.append({
                "role": "assistant",
                "content": reply
            })

            # Keep the latest 20 messages
            request.session["general_ai_history"] = history[-20:]
            request.session.modified = True

            return JsonResponse({"reply": reply})

        # All other therapy sections continue exactly as before.
        reply = get_ai_response(section, user_message)

        if user:
            ChatMessage.objects.create(
                user=user,
                section=section,
                role="user",
                content=user_message
            )

            ChatMessage.objects.create(
                user=user,
                section=section,
                role="assistant",
                content=reply
            )

        return JsonResponse({"reply": reply})

    chat_history = get_chat_history(user, section)

    return render(
        request,
        f'core/{section}.html',
        {"chat_history": chat_history}
    )


# ✅ NEW: Reset users but keep superuser/admin
def reset_users(request):
    # Delete all users except superuser accounts
    User.objects.filter(is_superuser=False).delete()

    # After deletion, redirect back to welcome page
    return redirect('welcome')