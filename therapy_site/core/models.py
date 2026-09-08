from django.db import models


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