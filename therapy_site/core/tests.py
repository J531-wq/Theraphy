from django.conf import settings
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from unittest.mock import patch

from .models import Blog, User


class BlogCreateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username='blogger',
            full_name='Blog Writer',
        )
        session = self.client.session
        session['user_id'] = self.user.id
        session.save()

    def test_valid_submission_creates_unpublished_post(self):
        response = self.client.post('/blog/create/', {
            'title': 'A Helpful Blog Post',
            'category': 'wellness',
            'excerpt': 'A short summary for this helpful article.',
            'content': 'This article contains enough text to meet the minimum content length.',
        })

        self.assertRedirects(response, '/blog/create/success/')
        blog = Blog.objects.get(title='A Helpful Blog Post')
        self.assertEqual(blog.author_user, self.user)
        self.assertFalse(blog.is_published)

    def test_missing_category_displays_validation_error(self):
        response = self.client.post('/blog/create/', {
            'title': 'A Helpful Blog Post',
            'excerpt': 'A short summary for this helpful article.',
            'content': 'This article contains enough text to meet the minimum content length.',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'This field is required.')
        self.assertFalse(Blog.objects.filter(title='A Helpful Blog Post').exists())

    def test_blog_detail_renders_one_shared_header_and_footer(self):
        blog = Blog.objects.create(
            title='A Published Article',
            slug='a-published-article',
            author='Blog Writer',
            category='wellness',
            excerpt='A short summary for this published article.',
            content='This published article contains enough text for a useful example.',
            is_published=True,
        )

        response = self.client.get(reverse('blog_detail', args=[blog.slug]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="site-chrome-header"', count=1)
        self.assertContains(response, 'class="site-chrome-footer"', count=1)


class AdminDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create(
            username="siteadmin",
            full_name="Site Admin",
            password=make_password("admin-password"),
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )

    def test_admin_login_opens_custom_dashboard(self):
        response = self.client.post(reverse("login"), {
            "username": "siteadmin",
            "password": "admin-password",
        })

        self.assertRedirects(response, reverse("admin_dashboard"))
        response = self.client.get(reverse("admin_dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Admin Dashboard")
        self.assertEqual(self.client.get(reverse("admin_create_post")).status_code, 200)

    def test_django_superuser_can_login_to_custom_dashboard(self):
        get_user_model().objects.create_superuser(
            username="django-admin",
            email="django-admin@example.com",
            password="admin-password",
        )

        response = self.client.post(reverse("login"), {
            "username": "django-admin",
            "password": "admin-password",
        })

        self.assertRedirects(response, reverse("admin_dashboard"))
        self.assertEqual(
            self.client.get(reverse("admin_dashboard")).status_code,
            200,
        )

    def test_regular_login_clears_a_previous_django_admin_session(self):
        django_admin = get_user_model().objects.create_superuser(
            username="django-admin",
            email="django-admin@example.com",
            password="admin-password",
        )
        self.client.force_login(django_admin)
        User.objects.create(
            username="member",
            full_name="Regular Member",
            password=make_password("member-password"),
            is_active=True,
        )

        self.client.post(reverse("login"), {
            "username": "member",
            "password": "member-password",
        })

        self.assertRedirects(
            self.client.get(reverse("admin_dashboard")),
            reverse("sections"),
        )

    def test_admin_can_create_published_post_from_custom_panel(self):
        self.client.post(reverse("login"), {
            "username": "siteadmin",
            "password": "admin-password",
        })

        post_data = {
            "title": "Admin-created wellness post",
            "category": "wellness",
            "author": "Site Admin",
            "excerpt": "A useful summary for this article.",
            "content": "This article contains enough text to pass the minimum content length requirement.",
            "publish_now": "on",
        }
        response = self.client.post(reverse("admin_create_post"), post_data)

        self.assertEqual(response.status_code, 200)
        post = Blog.objects.get(title="Admin-created wellness post")
        self.assertTrue(post.is_published)
        self.assertEqual(post.author_user, self.admin)

        post_data.pop("publish_now")
        self.client.post(reverse("admin_create_post"), post_data)
        duplicate_title_posts = Blog.objects.filter(
            title="Admin-created wellness post"
        )
        self.assertEqual(duplicate_title_posts.count(), 2)
        self.assertTrue(duplicate_title_posts.filter(slug__endswith="-1").exists())

    def test_non_admin_login_keeps_regular_destination(self):
        User.objects.create(
            username="member",
            full_name="Regular Member",
            password=make_password("member-password"),
            is_active=True,
        )

        response = self.client.post(reverse("login"), {
            "username": "member",
            "password": "member-password",
        })

        self.assertRedirects(response, reverse("sections"))

    def test_non_admin_is_returned_to_sections_from_custom_dashboard(self):
        User.objects.create(
            username="member",
            full_name="Regular Member",
            password=make_password("member-password"),
            is_active=True,
        )
        self.client.post(reverse("login"), {
            "username": "member",
            "password": "member-password",
        })

        response = self.client.get(reverse("admin_dashboard"))

        self.assertRedirects(response, reverse("sections"))


@override_settings(STORAGES={
   **settings.STORAGES,
   "staticfiles": {
       "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
   },
})
class AccountRecoveryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            username="recoverme",
            full_name="Recovery User",
            email="recoverme@example.com",
            password=make_password("old-password"),
            is_active=True,
        )

    @patch("core.views.send_reset_email", return_value=True)
    def test_recovery_accepts_username_or_case_insensitive_email(self, send_email):
        for identifier in ("recoverme", "RECOVERME@example.com"):
            with self.subTest(identifier=identifier):
                response = self.client.post(
                    reverse("forgot_password"),
                    {"username_or_email": identifier},
                )

                self.assertRedirects(response, reverse("verify_reset_code"))
                self.assertEqual(
                    self.client.session["reset_username"],
                    self.user.username,
                )

        self.assertEqual(send_email.call_count, 2)

    @patch("core.views.send_reset_email", return_value=True)
    def test_recovery_reports_unknown_username_or_email(self, send_email):
        response = self.client.post(
            reverse("forgot_password"),
            {"username_or_email": "unknown@example.com"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "could not find an account")
        send_email.assert_not_called()
