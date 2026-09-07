"""
URL configuration for therapy_site project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add a URL to urlpatterns:  path('', views.MyView.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from core import views

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', views.welcome, name='welcome'),

    path('login/', views.login_view, name='login'),

    path('register/', views.register_view, name='register'),

    # Email verification after registration
    path(
        'verify-email/',
        views.verify_email,
        name='verify_email'
    ),

    # Forgot password / username
    path(
        'forgot-password/',
        views.forgot_password,
        name='forgot_password'
    ),

    # Verification code for password / username recovery
    path(
        'verify-reset-code/',
        views.verify_reset_code,
        name='verify_reset_code'
    ),

    # Reset password
    path(
        'reset-password/',
        views.reset_password,
        name='reset_password'
    ),

    path('sections/', views.sections, name='sections'),

    # Therapy section AI chat routes
    path(
        'therapy/child/',
        views.child_therapy,
        name='child_therapy'
    ),

    path(
        'therapy/teen/',
        views.teen_therapy,
        name='teen_therapy'
    ),

    path(
        'therapy/trauma/',
        views.trauma_therapy,
        name='trauma_therapy'
    ),

    path(
    'therapy/general/',
    views.general_ai_search,
    name='general_ai_search'
),

    path(
        'therapy/addiction/',
        views.addiction_therapy,
        name='addiction_therapy'
    ),

    path(
        'therapy/family/',
        views.family_therapy,
        name='family_therapy'
    ),

    path(
        'therapy/relationship/',
        views.relationship_therapy,
        name='relationship_therapy'
    ),

    # Generic therapy section route
    path(
        'therapy/<str:section>/',
        views.therapy_section,
        name='therapy_section'
    ),

    # ✅ NEW route to reset users (preserves superuser)
    path(
        'reset/',
        views.reset_users,
        name='reset_users'
    ),
]