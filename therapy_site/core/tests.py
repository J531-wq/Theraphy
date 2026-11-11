from django.conf import settings
from django.test import TestCase
from django.test import override_settings
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from django.contrib.auth import get_user_model
from unittest.mock import patch

from .forms import BlogCreateForm
from .models import Blog, ChatMessage, PageView, User


class BlogCreateTests(TestCase):
    def test_article_content_drops_empty_rich_text_spacers(self):
        form = BlogCreateForm({
            "title": "A Helpful Blog Post",
            "category": "wellness",
            "excerpt": "A short summary for this helpful article.",
            "content": (
                "<p>First useful paragraph with sufficient content.</p>"
                "<p><br></p><p>  </p>"
                "<br><br><h2><br>Useful heading<br></h2><br><br>"
                "<p>Second useful paragraph with sufficient content.</p>"
            ),
        })

        self.assertTrue(form.is_valid(), form.errors)
        self.assertNotIn("<p><br></p>", form.cleaned_data["content"])
        self.assertIn("<h2>Useful heading</h2>", form.cleaned_data["content"])
        self.assertNotIn("<br><br>", form.cleaned_data["content"])

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

    def test_blog_detail_renders_safe_rich_content(self):
        blog = Blog.objects.create(
            title="Formatted Article",
            slug="formatted-article",
            author="Blog Writer",
            category="wellness",
            excerpt="A short summary for this formatted article.",
            content=(
                "<p>A <strong>formatted</strong> paragraph.</p>"
                "<script>alert('unsafe')</script>"
                "<img src=x onerror=alert(1)>"
            ),
            is_published=True,
        )

        response = self.client.get(reverse("blog_detail", args=[blog.slug]))

        self.assertContains(response, "<strong>formatted</strong>")
        self.assertNotContains(response, "alert(&#x27;unsafe&#x27;)")
        self.assertNotContains(response, "onerror=")


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
        create_response = self.client.get(reverse("admin_create_post"))
        self.assertEqual(create_response.status_code, 200)
        self.assertContains(create_response, 'contenteditable="true"')
        self.assertContains(create_response, 'id="image-dropzone"')

    @override_settings(STORAGES={
        **settings.STORAGES,
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    })
    def test_admin_dashboard_renders_with_the_shared_shell(self):
        self.client.post(reverse("login"), {
            "username": "siteadmin",
            "password": "admin-password",
        }, secure=True)

        response = self.client.get(reverse("admin_dashboard"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="admin-topbar"')

    def test_superuser_site_navigation_has_dashboard_and_sign_out(self):
        self.client.post(reverse("login"), {
            "username": "siteadmin",
            "password": "admin-password",
        }, secure=True)

        response = self.client.get(reverse("blog_list"), secure=True)

        self.assertContains(response, 'href="/admin-panel/">Dashboard</a>')
        self.assertContains(response, 'href="/logout/">Sign out</a>')
        self.assertNotContains(response, 'href="/login/">Sign in</a>')
        self.assertNotContains(response, 'href="/register/">Get started</a>')

    def test_sign_out_ends_superuser_session(self):
        self.client.post(reverse("login"), {
            "username": "siteadmin",
            "password": "admin-password",
        }, secure=True)

        self.client.get(reverse("logout"), secure=True)

        self.assertNotIn("_auth_user_id", self.client.session)

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
            "content": (
                "<h2>Editor-formatted post</h2>"
                "<p>This article contains enough text to pass the minimum "
                "content length requirement.</p>"
            ),
            "publish_now": "on",
        }
        response = self.client.post(reverse("admin_create_post"), post_data)

        self.assertEqual(response.status_code, 200)
        post = Blog.objects.get(title="Admin-created wellness post")
        self.assertTrue(post.is_published)
        self.assertEqual(post.author_user, self.admin)
        self.assertIn("<h2>", post.content)

        post_data.pop("publish_now")
        self.client.post(reverse("admin_create_post"), post_data)
        duplicate_title_posts = Blog.objects.filter(
            title="Admin-created wellness post"
        )
        self.assertEqual(duplicate_title_posts.count(), 2)
        self.assertTrue(duplicate_title_posts.filter(slug__endswith="-1").exists())

    def test_dashboard_chart_shows_daily_site_and_chat_impressions(self):
        ChatMessage.objects.create(
            user=self.admin,
            section="stress",
            role="user",
            content="I have been feeling stressed lately.",
        )
        PageView.objects.create()
        self.client.post(reverse("login"), {
            "username": "siteadmin",
            "password": "admin-password",
        })

        response = self.client.get(reverse("admin_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_site_views"], 1)
        self.assertEqual(response.context["total_chat_impressions"], 1)
        today = response.context["impressions_chart"][-1]
        self.assertEqual(today["site_views"], 1)
        self.assertEqual(today["chat_impressions"], 1)
        self.assertContains(response, "Site views &amp; therapy chat impressions")
        self.assertContains(response, 'id="admin-sidebar"')
        self.assertContains(response, 'id="admin-menu-toggle"')

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
class TherapyThemeTests(TestCase):
   def setUp(self):
       user = User.objects.create(
           username="therapyuser",
           full_name="Therapy User",
           is_active=True,
       )
       session = self.client.session
       session["user_id"] = user.id
       session.save()

   def test_each_therapy_page_receives_its_own_section_theme(self):
       sections = (
           "child",
           "teen",
           "trauma",
           "addiction",
           "family",
           "relationship",
           "stress",
       )
       for section in sections:
           with self.subTest(section=section):
               response = self.client.get(
                   reverse("therapy_section", args=[section])
               )

               self.assertEqual(response.status_code, 200)
               self.assertContains(
                   response,
                   f'data-therapy-section="{section}"',
               )
               self.assertContains(response, "core/therapy-themes.css")

       response = self.client.get(reverse("general_ai_search"))
       self.assertEqual(response.status_code, 200)
       self.assertContains(response, 'data-therapy-section="stress"')


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


class PageViewMiddlewareTests(TestCase):
    def test_public_html_is_counted_but_admin_and_static_pages_are_not(self):
        response = self.client.get(reverse("welcome"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(PageView.objects.count(), 1)

        self.client.get("/admin-panel/")
        self.client.get("/static/core/logo.png")
        self.assertEqual(PageView.objects.count(), 1)


@override_settings(STORAGES={
   **settings.STORAGES,
   "staticfiles": {
       "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
   },
})
class CreatorPostManagementTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create(
            username="postcreator",
            full_name="Post Creator",
            email="creator@example.com",
            is_active=True,
        )
        self.post = Blog.objects.create(
            title="A Creator Article",
            slug="a-creator-article",
            author=self.creator.full_name,
            category="wellness",
            excerpt="A helpful short summary.",
            content="This article contains enough useful information for readers.",
            author_user=self.creator,
            is_published=True,
            views_count=240,
        )
        session = self.client.session
        session["user_id"] = self.creator.id
        session.save()

    def test_creator_dashboard_lists_posts_views_and_management_actions(self):
        response = self.client.get(reverse("creator_dashboard"), secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Creator Dashboard")
        self.assertContains(response, "240")
        self.assertContains(response, reverse("blog_edit", args=[self.post.id]))
        self.assertContains(response, reverse("blog_delete", args=[self.post.id]))
        self.assertNotContains(response, 'class="site-chrome-footer"')

    def test_creator_post_form_has_rich_editor_and_no_footer(self):
        response = self.client.get(reverse("blog_create"), secure=True)

        self.assertContains(response, 'id="content-editor" contenteditable="true"')
        self.assertContains(response, 'input[type="file"].form-control::file-selector-button')
        self.assertNotContains(response, 'class="site-chrome-footer"')

    def test_creator_post_list_is_paginated(self):
        Blog.objects.bulk_create([
            Blog(
                title=f"Creator post {number}",
                slug=f"creator-post-{number}",
                author=self.creator.full_name,
                category="wellness",
                excerpt="A helpful short summary.",
                content="This article contains enough useful information for readers.",
                author_user=self.creator,
            )
            for number in range(11)
        ])

        response = self.client.get(reverse("creator_dashboard"), secure=True)

        self.assertEqual(len(response.context["posts"]), 10)
        self.assertContains(response, "Page 1 of 2")
        self.assertContains(response, "?post_page=2#my-posts")

    def test_withdrawal_without_bank_details_prompts_creator_to_add_them(self):
        response = self.client.post(reverse("request_withdrawal"), secure=True)

        self.assertRedirects(
            response,
            reverse("earnings_dashboard"),
            fetch_redirect_response=False,
        )
        response = self.client.get(reverse("earnings_dashboard"), secure=True)
        self.assertContains(response, "Add and save your bank account details")
        self.assertContains(response, 'href="#bank-details"')

    def test_creator_edit_resubmits_post_for_approval(self):
        response = self.client.post(
            reverse("blog_edit", args=[self.post.id]),
            {
                "title": "Updated Creator Article",
                "category": "wellness",
                "excerpt": "Updated summary for the new version.",
                "content": "This updated article includes more than fifty useful characters.",
            },
        )

        self.assertRedirects(response, reverse("creator_dashboard"))
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Updated Creator Article")
        self.assertFalse(self.post.is_published)

    def test_creator_cannot_edit_or_delete_another_users_post(self):
        another_post = Blog.objects.create(
            title="Another Creator Article",
            slug="another-creator-article",
            author="Someone Else",
            excerpt="A different summary.",
            content="This article belongs to someone else and should stay protected.",
        )

        self.assertEqual(
            self.client.get(
                reverse("blog_edit", args=[another_post.id])
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                reverse("blog_delete", args=[another_post.id])
            ).status_code,
            404,
        )
        self.assertTrue(Blog.objects.filter(id=another_post.id).exists())

    def test_creator_can_delete_their_own_post(self):
        response = self.client.post(reverse("blog_delete", args=[self.post.id]))

        self.assertRedirects(response, reverse("creator_dashboard"))
        self.assertFalse(Blog.objects.filter(id=self.post.id).exists())

    def test_therapy_dashboard_separates_creator_tools_from_therapy_choices(self):
        response = self.client.get(reverse("sections"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Creator Studio")
        self.assertContains(response, reverse("creator_dashboard"))
        self.assertNotContains(response, "Earnings Dashboard")


class AdminPostManagementTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser(
            username="post-admin",
            email="post-admin@example.com",
            password="admin-password",
        )
        self.creator = User.objects.create(
            username="reviewedcreator",
            full_name="Reviewed Creator",
            email="reviewed@example.com",
            is_active=True,
        )
        self.post = Blog.objects.create(
            title="Approved Article",
            slug="approved-article",
            author=self.creator.full_name,
            category="wellness",
            excerpt="Approved article summary.",
            content="This approved article contains enough content for readers.",
            author_user=self.creator,
            is_published=True,
            views_count=315,
        )
        self.client.force_login(self.admin)

    def test_admin_approved_filter_keeps_approved_posts_separate(self):
        Blog.objects.create(
            title="Awaiting Review",
            slug="awaiting-review",
            author="New Creator",
            excerpt="Pending summary.",
            content="This pending article contains enough content for review.",
        )

        response = self.client.get(
            reverse("admin_posts"), {"status": "approved"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Approved Article")
        self.assertNotContains(response, "Awaiting Review")
        self.assertContains(response, "315 views")

    @patch("core.views.notify_subscribers_of_new_post", return_value=1)
    @patch("core.views.send_blog_post_approved_email", return_value=True)
    def test_approved_post_stays_in_approved_section(
        self, send_approved_email, notify_subscribers
    ):
        pending_post = Blog.objects.create(
            title="Newly Approved Article",
            slug="newly-approved-article",
            author=self.creator.full_name,
            excerpt="A pending article summary.",
            content="This pending article is long enough to approve and publish.",
            author_user=self.creator,
            moderation_reason="Previous review reason.",
        )

        response = self.client.post(
            reverse("admin_approve_blog", args=[pending_post.id])
        )

        self.assertRedirects(
            response, f"{reverse('admin_posts')}?status=approved"
        )
        pending_post.refresh_from_db()
        self.assertTrue(pending_post.is_published)
        self.assertEqual(pending_post.moderation_reason, "")
        approved_response = self.client.get(
            reverse("admin_posts"), {"status": "approved"}
        )
        self.assertContains(approved_response, "Newly Approved Article")
        send_approved_email.assert_called_once()
        notify_subscribers.assert_called_once()

    def test_admin_can_edit_post_without_changing_approval_status(self):
        response = self.client.post(
            reverse("admin_edit_blog", args=[self.post.id]),
            {
                "title": "Admin Updated Article",
                "category": "wellness",
                "excerpt": "Updated article summary.",
                "content": "An administrator has updated this article with enough useful content.",
            },
        )

        self.assertRedirects(response, reverse("admin_posts"))
        self.post.refresh_from_db()
        self.assertEqual(self.post.title, "Admin Updated Article")
        self.assertTrue(self.post.is_published)

    @patch("core.views.send_blog_post_removed_email", return_value=True)
    def test_admin_removal_requires_reason_and_emails_creator(self, send_email):
        response = self.client.post(
            reverse("admin_remove_blog", args=[self.post.id]),
            {"reason": "  "},
        )
        self.assertRedirects(
            response, f"{reverse('admin_posts')}?status=approved"
        )
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published)
        send_email.assert_not_called()

        reason = "This post includes a claim that needs correction."
        response = self.client.post(
            reverse("admin_remove_blog", args=[self.post.id]),
            {"reason": reason},
        )

        self.assertRedirects(response, f"{reverse('admin_posts')}?status=removed")
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_published)
        self.assertEqual(self.post.moderation_reason, reason)
        send_email.assert_called_once()

    def test_removed_reason_is_visible_to_its_creator(self):
        self.post.is_published = False
        self.post.moderation_reason = "Please update your references."
        self.post.save()
        self.client.logout()
        session = self.client.session
        session["user_id"] = self.creator.id
        session.save()

        response = self.client.get(reverse("creator_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Please update your references.")
        self.assertContains(response, "Removed")
