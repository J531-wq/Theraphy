from django.contrib import admin
from .models import User, Blog, ChatSession, ChatMessage


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
    list_display = ('title', 'author', 'category', 'is_published', 'created_at')
    list_filter = ('is_published', 'category', 'created_at')
    search_fields = ('title', 'author', 'content')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        ('Blog Information', {
            'fields': ('title', 'slug', 'author', 'category')
        }),
        ('Content', {
            'fields': ('excerpt', 'content', 'featured_image')
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