from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from admin_panel.models import Category
from admin_panel.forms import CategoryForm



def admin_required(view_func):
    return user_passes_test(
        lambda user: (
            user.is_authenticated
            and user.is_active
            and user.is_staff
            and user.is_superuser
        ),
        login_url='admin_panel:admin_login'
    )(view_func)


@admin_required
def category_list(request):
    categories = Category.objects.all().order_by("-created_at", "-pk")

    context = {
        "categories": categories,
    }

    return render(
        request,
        "admin_panel/category_list.html",
        context,
    )

@admin_required
def category_add(request):

    if request.method == "POST":
        form = CategoryForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, "Category added successfully.")
            return redirect("admin_panel:category_list")

    else:
        form = CategoryForm()

    return render(
        request,
        "admin_panel/category_form.html",
        {
            "form": form,
            "page_title": "Add Category",
            "button_text": "Add Category",
        },
    )


@admin_required
def category_edit(request, pk):

    category = get_object_or_404(Category, pk=pk)

    if request.method == "POST":
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            messages.success(request, "Category updated successfully.")
            return redirect("admin_panel:category_list")

    else:
        form = CategoryForm(instance=category)

    return render(
        request,
        "admin_panel/category_form.html",
        {
            "form": form,
            "page_title": "Edit Category",
            "button_text": "Save Changes",
        },
    )

@admin_required
def category_toggle_status(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:category_list")

    category = get_object_or_404(Category, pk=pk)

    category.is_active = not category.is_active
    category.save(update_fields=["is_active"])

    if category.is_active:
        messages.success(
            request,
            f'"{category.name}" activated successfully.',
        )
    else:
        messages.success(
            request,
            f'"{category.name}" blocked successfully.',
        )

    return redirect("admin_panel:category_list")