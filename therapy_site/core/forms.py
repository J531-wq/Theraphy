from django import forms
from django.contrib.auth.hashers import make_password
from .models import User


class RegisterForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password'
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your password'
        })
    )

    class Meta:
        model = User
        fields = [
            'username',
            'full_name',
            'email',
            'password',
            'confirm_password',
        ]

        widgets = {
            'username': forms.TextInput(attrs={
                'placeholder': 'Enter your username'
            }),

            'full_name': forms.TextInput(attrs={
                'placeholder': 'Enter your full name'
            }),

            'email': forms.EmailInput(attrs={
                'placeholder': 'Enter your email address'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError(
                    'Passwords do not match.'
                )

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        # Securely hash the password before saving it.
        user.password = make_password(
            self.cleaned_data['password']
        )

        if commit:
            user.save()

        return user


class LoginForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password'
        })
    )


class ForgotPasswordForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your username'
        })
    )


class VerificationCodeForm(forms.Form):
    verification_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter verification code',
            'maxlength': '6',
            'inputmode': 'numeric'
        })
    )


class ResetPasswordForm(forms.Form):
    username = forms.CharField(
        max_length=50,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter your new username'
        })
    )

    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your new password'
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Confirm your new password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()

        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if not username:
            raise forms.ValidationError(
                'Please enter a new username.'
            )

        if password and confirm_password:
            if password != confirm_password:
                raise forms.ValidationError(
                    'Passwords do not match.'
                )

        return cleaned_data