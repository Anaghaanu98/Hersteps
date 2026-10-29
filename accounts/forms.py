
from django import forms
from django.contrib.auth import get_user_model
import re
from django.contrib.auth.password_validation import validate_password
User = get_user_model()

class SignupForm(forms.Form):
    fullname = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "Enter your full name",
            "class": "form-input",
            "autocomplete": "name",
        })
    )

    username = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            "placeholder": "Choose a username",
            "class": "form-input",
            "autocomplete": "username",
        })
    )

    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            "placeholder": "Enter your email address",
            "class": "form-input",
            "autocomplete": "email",
        })
    )

    password = forms.CharField(
        min_length=8,
        widget=forms.PasswordInput(attrs={
            "placeholder": "Create a strong password",
            "class": "form-input",
            "autocomplete": "new-password",
        })
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            "placeholder": "Re-enter your password",
            "class": "form-input",
            "autocomplete": "new-password",
        })
    )
    def clean_fullname(self):
        fullname = self.cleaned_data.get("fullname", "").strip()

        
        if not re.fullmatch(
            r"[^\W\d_]+(?: [^\W\d_]+)*",fullname):
            raise forms.ValidationError(
                "Enter a valid full name using letters and  spaces only."
            )

        if len(fullname) < 3:
            raise forms.ValidationError(
                "Full name must contain at least 3 characters."
            )

        return fullname
    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if not re.fullmatch(r"(?=.*[A-Za-z0-9])[A-Za-z0-9_]{3,30}", username):
            raise forms.ValidationError(
                "Username must be 3–30 characters and contain "
            "at least one letter or number. Only letters, numbers "
            "and underscores are allowed."
            )
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError(
                "This username is already taken."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def clean(self):
        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password:
            try:
                validate_password(password)
            except forms.ValidationError as error:
                self.add_error('password',error)
        if password and confirm_password:
            if password != confirm_password:
                self.add_error(
                    "confirm_password",
                    "Passwords do not match."
                )

        return cleaned_data

    