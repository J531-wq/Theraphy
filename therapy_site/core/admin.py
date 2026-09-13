from django.contrib import admin
from django.urls import reverse

from .models import (
    Blog,
    BlogComment,
    BlogCommentVote,
    BlogPostLike,
    BlogSubscriber,
    ChatMessage,
    ChatSession,
    User,
)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'is_active', 'created_date')
    search_fields = ('username', 'full_name', 'email')
    list_filter = ('is_active',)
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'full_name', 'email')
        }),
        ('Account Status', {
            'fields': ('is_active',)
        }),
        ('Security', {
            'fields': ('password',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('username',)
    
    def created_date(self, obj):
        return "N/A"  # You can add created_at field to User model if needed
    created_date.short_description = 'Created'


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'category', 'is_published', 'likes_count', 'created_at')
    list_filter = ('is_published', 'category', 'created_at')
    search_fields = ('title', 'author', 'content')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Blog Information', {
            'fields': ('title', 'slug', 'author', 'category')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'featured_image', 'cover_image_url')
        }),
        ('Publication Status', {
            'fields': ('is_published',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

    def save_model(self, request, obj, form, change):
        """Notify active subscribers the first time a post is published."""
        was_published = False
        if change:
            try:
                was_published = Blog.objects.get(pk=obj.pk).is_published
            except Blog.DoesNotExist:
                was_published = False
        super().save_model(request, obj, form, change)
        if obj.is_published and not was_published:
            try:
                from .services.email_service import (
                    notify_subscribers_of_new_post,
                )
                base_url = (
                    f"{request.scheme}://{request.get_host()}"
                ).rstrip('/')
                notify_subscribers_of_new_post(obj, base_url)
            except Exception:  # never break saving the post
                import logging
                logging.getLogger(__name__).exception(
                    "Failed to notify subscribers about '%s'", obj.slug
                )


@admin.register(BlogSubscriber)
class BlogSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('email', 'name')
    readonly_fields = ('token', 'created_at')


@admin.register(BlogComment)
class BlogCommentAdmin(admin.ModelAdmin):
    list_display = ('name', 'post', 'is_approved', 'likes_count', 'dislikes_count', 'created_at')
    list_filter = ('is_approved', 'created_at')
    search_fields = ('name', 'email', 'body')
    readonly_fields = ('created_at',)


@admin.register(BlogCommentVote)
class BlogCommentVoteAdmin(admin.ModelAdmin):
    list_display = ('comment', 'value', 'created_at')
    list_filter = ('value',)
    readonly_fields = ('created_at',)


@admin.register(BlogPostLike)
class BlogPostLikeAdmin(admin.ModelAdmin):
    list_display = ('post', 'created_at')
    readonly_fields = ('created_at',)


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'section', 'created_at')
    list_filter = ('section', 'created_at')
    search_fields = ('title', 'user__username')
    readonly_fields = ('created_at',)


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('user', 'section', 'role', 'created_at')
    list_filter = ('section', 'role', 'created_at')
    search_fields = ('user__username', 'content')
    readonly_fields = ('created_at',)