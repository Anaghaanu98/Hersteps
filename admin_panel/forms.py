from django import forms
from .models import Category


class CategoryForm(forms.ModelForm):

    class Meta:
        model = Category
        fields = ["name", "is_active"]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter category name",
            }),
            
            "is_active": forms.Select(
                choices=[
                    (True, "Active"),
                    (False, "Blocked"),
                ],
                attrs={"class": "form-control"},
            ),
        }