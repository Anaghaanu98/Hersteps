from django import forms
from admin_panel.models import Category
from django.db.models.functions import Lower
from admin_panel.models import Category, Product
import re





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

    def clean_name(self):
        name = self.cleaned_data.get("name", "")

        
        if name != name.strip():
            raise forms.ValidationError(
                "Category name must not start or end with spaces."
            )

        if not name:
            raise forms.ValidationError(
                "Category name is required."
            )

        if not name.strip():
            raise forms.ValidationError(
                "Category name cannot contain only spaces."
            )

        if not re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)*", name):
            raise forms.ValidationError(
                "Category name must contain only alphabets and spaces. "
                "Numbers and special characters are not allowed."
            )

        # Prevent duplicate names, ignoring letter case.
        duplicate = Category.objects.annotate(
            lowercase_name=Lower("name")
        ).filter(
            lowercase_name=name.lower()
        )

        if self.instance and self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                "A category with this name already exists."
            )

        return name


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            "name",
            "description",
            "category",
            "color",
            "occasion",
            "price",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Enter product name",
            }),

            "description": forms.Textarea(attrs={
                "placeholder": "Enter product description",
                "rows": 4,
            }),

            "category": forms.Select(),

            "color": forms.Select(),

            "occasion": forms.Select(),

            "price": forms.NumberInput(attrs={
                "placeholder": "Enter price",
                "min": "0.01",
                "step": "0.01",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        )

    def clean_name(self):
        name = self.cleaned_data.get("name", "")

        if name != name.strip():
            raise forms.ValidationError(
                "Product name must not start or end with spaces."
            )

        if not name:
            raise forms.ValidationError(
                "Product name is required."
            )

        if not name.strip():
            raise forms.ValidationError(
                "Product name cannot contain only spaces."
            )

        if not re.fullmatch(r"[A-Za-z]+(?: [A-Za-z]+)*", name):
            raise forms.ValidationError(
                "Product name must contain only alphabets and spaces. "
                "Numbers and special characters are not allowed."
            )

        # Prevent duplicate product names, ignoring letter case.
        duplicate = Product.objects.annotate(
            lowercase_name=Lower("name")
        ).filter(
            lowercase_name=name.lower()
        )

        if self.instance and self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if duplicate.exists():
            raise forms.ValidationError(
                "A product with this name already exists."
            )

        return name

    def clean_category(self):
        category = self.cleaned_data.get("category")

        if category is None:
            raise forms.ValidationError(
                "Please select a category."
            )

        if not category.is_active:
            raise forms.ValidationError(
                "This category is blocked. Please select an active category."
            )

        return category

    def clean_price(self):
        price = self.cleaned_data.get("price")

        if price is None:
            raise forms.ValidationError(
                "Price is required."
            )

        if price <= 0:
            raise forms.ValidationError(
                "Price must be greater than zero."
            )

        return price
