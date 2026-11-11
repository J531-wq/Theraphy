from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError

from core.models import User


class Command(BaseCommand):
    help = "Create an admin (staff/superuser) account in the custom core.User model."

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="Admin username")
        parser.add_argument("--email", type=str, default="", help="Admin email")
        parser.add_argument("--password", type=str, help="Admin password")

    def handle(self, *args, **options):
        username = options.get("username")
        email = options.get("email") or ""
        password = options.get("password")

        if not username:
            username = input("Username: ").strip()
        if not username:
            raise CommandError("Username is required.")
        if not password:
            import getpass
            password = getpass.getpass("Password: ")
        if not password:
            raise CommandError("Password is required.")

        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists.")

        user = User.objects.create(
            username=username,
            full_name=username,
            email=email or None,
            password=make_password(password),
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Site admin '{user.username}' created (id={user.id}). "
                "You can now log in at /login/ and access /admin/."
            )
        )
