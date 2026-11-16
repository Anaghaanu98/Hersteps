from django import forms
from my_accounts.forms import AddressForm


class CheckoutAddressForm(AddressForm):

    class Meta(AddressForm.Meta):
        fields = [
            "full_name",
            "phone",
            "house_name",
            "locality",
            "city",
            "state",
            "pincode",
        ]
    