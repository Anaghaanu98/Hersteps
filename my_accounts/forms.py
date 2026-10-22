
from django import forms
from django.contrib.auth import get_user_model
from .models import Address
User = get_user_model()


class ProfileUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            "fullname",
            "username",
            "phone_number",
        ]

    def clean_username(self):
        username = self.cleaned_data["username"].strip()

        existing_user = User.objects.filter(
            username__iexact=username
        ).exclude(pk=self.instance.pk)

        if existing_user.exists():
            raise forms.ValidationError(
                "This username is already taken."
            )

        return username

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get("phone_number", "")
        return phone_number.strip()

class AddressForm(forms.ModelForm):
    class Meta:
        model=Address
        fields=['full_name','phone','house_name','locality','city','state','pincode','address_type',]
        widgets={'address_type':forms.RadioSelect(),}