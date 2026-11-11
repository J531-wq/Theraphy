from django.test import TestCase

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
