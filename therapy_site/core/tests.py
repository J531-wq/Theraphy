from django.test import TestCase
from django.urls import reverse

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
