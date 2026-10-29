
from django import forms
from django.contrib.auth import get_user_model
from .models import Address
User = get_user_model()
import re

class ProfileUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = [
            "fullname",
            "username",
            "phone_number",
        ]
    def clean_fullname(self):
        fullname = self.cleaned_data.get("fullname", "").strip()

        if not fullname:
            raise forms.ValidationError(
                "Full name is required."
            )

        if len(fullname) < 2:
            raise forms.ValidationError(
                "Full name must contain at least 2 characters."
            )

        return fullname
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
        widgets = {
            "full_name": forms.TextInput(attrs={
                "placeholder": "Enter full name",
                "maxlength": "150",
            }),
            "phone": forms.TextInput(attrs={
                "placeholder": "+91 XXXXX XXXXX",
                "inputmode": "tel",
                "maxlength": "14",
            }),
            "address_type": forms.RadioSelect(),
            "house_name": forms.TextInput(attrs={
                "placeholder": "House number, street name",
                "maxlength": "255",
            }),
            "locality": forms.TextInput(attrs={
                "placeholder": "Area or locality",
                "maxlength": "150",
            }),
            "city": forms.TextInput(attrs={
                "placeholder": "City",
                "maxlength": "100",
            }),
            "state": forms.TextInput(attrs={
                "placeholder": "State",
                "maxlength": "100",
            }),
            "pincode": forms.TextInput(attrs={
                "placeholder": "6-digit PIN code",
                "maxlength": "6",
                "inputmode": "numeric",
            }),
        }
      # Remove unnecessary spaces from text fields
    def clean_full_name(self):
        value = self.cleaned_data['full_name'].strip()

        if not value:
            raise forms.ValidationError("Full name is required.")

        if not re.fullmatch(
            r"[^\W\d_]+(?:[ .'-][^\W\d_]+)*",
            value,
            flags=re.UNICODE,
        ):
            raise forms.ValidationError(
                "Enter a valid full name using letters only."
            )

        return value

    def clean_phone(self):
        phone = self.cleaned_data['phone'].strip()

        # Allow spaces and hyphens in the phone number
        normalized_phone = re.sub(r"[\s-]", "", phone)

        # Remove the optional Indian country code
        if normalized_phone.startswith("+91"):
            normalized_phone = normalized_phone[3:]

        # Validate the 10-digit Indian mobile number
        if not re.fullmatch(r"[6-9]\d{9}", normalized_phone):
            raise forms.ValidationError(
                "Enter a valid 10-digit Indian mobile number."
            )

        return normalized_phone
    def clean_house_name(self):
        value = self.cleaned_data['house_name'].strip()

        if not value:
            raise forms.ValidationError(
                "House name or street address is required."
            )

        if not re.fullmatch(r'(?=.*[A-Za-z0-9])[A-Za-z0-9 -]+', value):
                  raise forms.ValidationError(
                    "Use only letters, numbers, spaces, and hyphens. "
                    "The address cannot contain only hyphens."
                )
        return value

    def clean_locality(self):
        value = self.cleaned_data['locality'].strip()

        if not value:
            raise forms.ValidationError("Locality is required.")

        if not re.fullmatch(r'(?=.*[A-Za-z0-9])[A-Za-z0-9 -]+', value):
                  raise forms.ValidationError(
                    "Use only letters, numbers, spaces, and hyphens. "
                    "The address cannot contain only hyphens."
                )
        return value

    def clean_city(self):
        value = self.cleaned_data['city'].strip()

        if not value:
            raise forms.ValidationError("City is required.")

        if not re.fullmatch(r'[A-Za-z ]+', value):
            raise forms.ValidationError(
            "City must contain only letters and spaces."
        )

        return value
    def clean_state(self):
        value = self.cleaned_data['state'].strip()

        if not value:
            raise forms.ValidationError("State is required.")

        if not re.fullmatch(
        r"(?=.*[^\W\d_])[^\W\d_]+(?:[ -][^\W\d_]+)*",
        value,
        flags=re.UNICODE,
            ):
          raise forms.ValidationError(
              "State must contain only letters, spaces, and hyphens."
            )
        return value

    def clean_pincode(self):
        pincode = self.cleaned_data['pincode'].strip()

        if not re.fullmatch(r"[1-9]\d{5}", pincode):
            raise forms.ValidationError(
                "Enter a valid 6-digit Indian PIN code."
            )

        return pincode    