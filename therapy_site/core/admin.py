import logging

from django.contrib import admin
from django.utils import timezone

from .models import (
    Blog,
    BlogComment,
    BlogCommentVote,
    BlogPostLike,
    BlogSubscriber,
    ChatMessage,
    ChatSession,
    User,
    WithdrawalRequest,
)

logger = logging.getLogger(__name__)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'full_name', 'email', 'is_active', 'is_staff', 'is_superuser', 'has_bank_details')
    search_fields = ('username', 'full_name', 'email')
    list_filter = ('is_active', 'is_staff', 'is_superuser')
    fieldsets = (
        ('User Information', {
            'fields': ('username', 'full_name', 'email')
        }),
        ('Account Status', {
            'fields': ('is_active', 'is_staff', 'is_superuser')
        }),
        ('Bank / Payout Details', {
            'fields': ('bank_name', 'account_number', 'account_name'),
        }),
        ('Security', {
            'fields': ('password',),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('username',)

    def has_bank_details(self, obj):
        return bool(obj.bank_name and obj.account_number)
    has_bank_details.boolean = True
    has_bank_details.short_description = 'Bank set?'


@admin.register(Blog)
class BlogAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'author_user', 'category', 'is_published', 'views_count', 'likes_count', 'created_at')
    list_filter = ('is_published', 'category', 'created_at')
    search_fields = ('title', 'author', 'content')
    prepopulated_fields = {'slug': ('title',)}
    autocomplete_fields = ['author_user']
    fieldsets = (
        ('Blog Information', {
            'fields': ('title', 'slug', 'author', 'author_user', 'category')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'featured_image', 'cover_image_url')
        }),
        ('Publication Status', {
            'fields': ('is_published',)
        }),
        ('Stats', {
            'fields': ('views_count', 'likes_count'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at', 'views_count', 'likes_count')

    def save_model(self, request, obj, form, change):
        """
        1. Notify subscribers when a post is first published.
        2. Notify the author_user when their submitted post is approved.
        """
        was_published = False
        if change:
            try:
                was_published = Blog.objects.get(pk=obj.pk).is_published
            except Blog.DoesNotExist:
                was_published = False
        super().save_model(request, obj, form, change)
        if obj.is_published and not was_published:
            base_url = f"{request.scheme}://{request.get_host()}".rstrip('/')
            # Notify blog subscribers
            try:
                from .services.email_service import notify_subscribers_of_new_post
                notify_subscribers_of_new_post(obj, base_url)
            except Exception:
                logger.exception("Failed to notify subscribers about '%s'", obj.slug)
            # Notify user author (if any)
            if obj.author_user and obj.author_user.email:
                try:
                    from .services.email_service import send_blog_post_approved_email
                    send_blog_post_approved_email(obj.author_user, obj, base_url)
                except Exception:
                    logger.exception(
                        "Failed to notify author '%s' about approved post '%s'",
                        obj.author_user.username, obj.slug
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


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'bank_name', 'account_number', 'account_name', 'status', 'created_at', 'sent_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username', 'user__email', 'account_name', 'account_number')
    readonly_fields = ('created_at', 'sent_at')
    actions = ['mark_as_sent']

    def mark_as_sent(self, request, queryset):
        """Admin bulk action — mark selected withdrawal requests as sent."""
        from .services.email_service import send_withdrawal_sent_email
        sent_count = 0
        for withdrawal in queryset.filter(status=WithdrawalRequest.STATUS_PENDING):
            withdrawal.status = WithdrawalRequest.STATUS_SENT
            withdrawal.sent_at = timezone.now()
            withdrawal.save()
            if withdrawal.user.email:
                try:
                    send_withdrawal_sent_email(withdrawal.user, withdrawal)
                except Exception:
                    logger.exception(
                        "Failed to email user '%s' for withdrawal #%s",
                        withdrawal.user.username, withdrawal.id
                    )
            sent_count += 1
        self.message_user(request, f"{sent_count} withdrawal(s) marked as sent.")
    mark_as_sent.short_description = "Mark selected as Sent & email users"
