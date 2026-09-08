"""
Email service for MyTherapyDoctor.

All outgoing emails are sent via ZeptoMail SMTP using Django's
built-in email backend.  Each function renders an HTML template,
attaches a plain-text fallback, and calls send_mail / EmailMultiAlternatives.
"""

import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


def _send(subject: str, to_email: str, template: str, context: dict) -> bool:
    """
    Render *template* with *context*, then send a multipart email
    (HTML + plain-text fallback) to *to_email*.

    Returns True on success, False on failure (errors are logged).
    """
    try:
        html_body = render_to_string(template, context)
        text_body = strip_tags(html_body)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_body, "text/html")
        msg.send(fail_silently=False)
        return True

    except SMTPException as exc:
        logger.error(
            "SMTPException sending '%s' to %s: %s",
            subject, to_email, exc, exc_info=True,
        )
        return False
    except OSError as exc:
        logger.error(
            "OSError sending '%s' to %s: %s",
            subject, to_email, exc, exc_info=True,
        )
        return False
    except Exception as exc:          # noqa: BLE001
        logger.error(
            "Unexpected error sending '%s' to %s: %s",
            subject, to_email, exc, exc_info=True,
        )
        return False


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def send_verification_email(user) -> bool:
    """
    Send the email-address verification code to a newly registered user.

    The caller is responsible for generating the code and storing it in
    the session **before** calling this function.  Pass the plain-text
    code as ``user.verification_code`` (a temporary attribute set in the
    view) so we never touch the database here.
    """
    return _send(
        subject="Verify Your Email – MyTherapyDoctor",
        to_email=user.email,
        template="core/emails/verification_email.html",
        context={
            "full_name": user.full_name,
            "verification_code": user.verification_code,
        },
    )


def send_reset_email(user, reset_code: str) -> bool:
    """
    Send a password / username recovery code to the user's registered email.
    """
    return _send(
        subject="Account Recovery – MyTherapyDoctor",
        to_email=user.email,
        template="core/emails/reset_email.html",
        context={
            "full_name": user.full_name,
            "reset_code": reset_code,
        },
    )


def send_welcome_email(user) -> bool:
    """
    Send a welcome email after the user successfully verifies their account.
    Failures are logged but do not block the user from proceeding.
    """
    return _send(
        subject="Welcome to MyTherapyDoctor 🌿",
        to_email=user.email,
        template="core/emails/welcome_email.html",
        context={
            "full_name": user.full_name,
            "username": user.username,
        },
    )
