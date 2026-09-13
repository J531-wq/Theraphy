import uuid

from django.db import models
from django.urls import reverse


class User(models.Model):
    username = models.CharField(max_length=50, unique=True)
    full_name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, null=True, blank=True)
    password = models.CharField(max_length=128, null=True, blank=True)
    is_active = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class ChatSession(models.Model):
    """
    One chat session per user per therapy section.
    A user can have many sessions per section (chat history).
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions'
    )
    section = models.CharField(max_length=50)
    title = models.CharField(max_length=120, default='New Conversation')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} — {self.section} — {self.title}"


class ChatMessage(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_messages'
    )
    # Optional FK to ChatSession — null for legacy rows
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        null=True,
        blank=True,
    )
    section = models.CharField(max_length=50)
    role = models.CharField(max_length=20)   # "user" or "assistant"
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user.username} - {self.section} - {self.role}"


class Blog(models.Model):
    """
    Blog post model with rich content and metadata.
    """
    CATEGORY_CHOICES = [
        ('mental_health', 'Mental Health'),
        ('wellness', 'Wellness'),
        ('therapy', 'Therapy'),
        ('tips', 'Tips & Advice'),
        ('success_stories', 'Success Stories'),
        ('other', 'Other'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    author = models.CharField(max_length=100)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='other')
    content = models.TextField()
    excerpt = models.TextField(max_length=500, help_text="Short summary of the blog post")
    featured_image = models.ImageField(upload_to='blog_images/', null=True, blank=True)
    cover_image_url = models.URLField(
        max_length=500, null=True, blank=True,
        help_text="External cover photo URL (used when no uploaded featured image)",
    )
    likes_count = models.PositiveIntegerField(default=0)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('blog_detail', args=[self.slug])


class BlogSubscriber(models.Model):
    """Email subscriber for new-blog-post notifications (ZeptoMail)."""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True, default='')
    is_active = models.BooleanField(default=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.email


class BlogComment(models.Model):
    """Reader comment on a blog post. Replies nest one level via `parent`."""
    post = models.ForeignKey(
        Blog, on_delete=models.CASCADE, related_name='comments'
    )
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE,
        related_name='replies', null=True, blank=True,
    )
    name = models.CharField(max_length=100)
    email = models.EmailField()
    body = models.TextField(max_length=2000)
    is_approved = models.BooleanField(default=True)
    likes_count = models.PositiveIntegerField(default=0)
    dislikes_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.name} on {self.post.slug}"

    @property
    def score(self):
        return self.likes_count - self.dislikes_count


class BlogCommentVote(models.Model):
    """One like (+1) or dislike (-1) per visitor per comment."""
    LIKE = 1
    DISLIKE = -1
    VALUE_CHOICES = [(LIKE, 'Like'), (DISLIKE, 'Dislike')]

    comment = models.ForeignKey(
        BlogComment, on_delete=models.CASCADE, related_name='votes'
    )
    voter_key = models.CharField(max_length=64, db_index=True)
    value = models.SmallIntegerField(choices=VALUE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['comment', 'voter_key'],
                name='unique_comment_voter',
            )
        ]

    def __str__(self):
        return f"{self.voter_key} → {self.value} on comment {self.comment_id}"


class BlogPostLike(models.Model):
    """One like per visitor per blog post."""
    post = models.ForeignKey(
        Blog, on_delete=models.CASCADE, related_name='likes'
    )
    voter_key = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['post', 'voter_key'],
                name='unique_post_voter',
            )
        ]

    def __str__(self):
        return f"{self.voter_key} likes {self.post.slug}"