from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.exceptions import ValidationError

from admin_panel.models import Banner
from admin_panel.decorators import admin_required


@admin_required
def banner_list(request):
    banners = Banner.objects.all().order_by("-created_at", "-pk")

    return render(
        request,
        "admin_panel/banner_list.html",
        {"banners": banners},
    )


@admin_required
def banner_add(request):
    if request.method == "POST":
        banner = Banner(
            name=request.POST.get("name", ""),
            is_active=request.POST.get("is_active") == "True",
        )

        image = request.FILES.get("image")

        if image:
            banner.image = image

        try:
            if not image:
                raise ValidationError(
                    "Please select a banner image."
                )

            banner.save()

            messages.success(
                request,
                "Banner added successfully.",
            )
            return redirect("admin_panel:banner_list")

        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for field_errors in error.message_dict.values():
                    for error_message in field_errors:
                        messages.error(request, error_message)
            else:
                for error_message in error.messages:
                    messages.error(request, error_message)

    return render(
        request,
        "admin_panel/add_edit_banner.html",
        {"banner": None},
    )


@admin_required
def banner_edit(request, banner_id):
    banner = get_object_or_404(Banner, pk=banner_id)

    if request.method == "POST":
        banner.name = request.POST.get("name", "")
        banner.is_active = request.POST.get("is_active") == "True"

        image = request.FILES.get("image")

        # Keep the existing image unless a replacement is uploaded.
        if image:
            banner.image = image

        try:
            banner.save()

            messages.success(
                request,
                "Banner updated successfully.",
            )
            return redirect("admin_panel:banner_list")

        except ValidationError as error:
            if hasattr(error, "message_dict"):
                for field_errors in error.message_dict.values():
                    for error_message in field_errors:
                        messages.error(request, error_message)
            else:
                for error_message in error.messages:
                    messages.error(request, error_message)

    return render(
        request,
        "admin_panel/add_edit_banner.html",
        {"banner": banner},
    )

@admin_required
def banner_toggle_status(request, banner_id):
    if request.method != "POST":
        return redirect("admin_panel:banner_list")

    banner = get_object_or_404(Banner, pk=banner_id)

    # Toggle the current status
    banner.is_active = not banner.is_active

    try:
        banner.save()
        messages.success(
            request,
            f"Banner '{banner.name}' status updated successfully."
        )
    except ValidationError as error:
        if hasattr(error, "message_dict"):
            for field_errors in error.message_dict.values():
                for error_message in field_errors:
                    messages.error(request, error_message)
        else:
            for error_message in error.messages:
                messages.error(request, error_message)

    return redirect("admin_panel:banner_list")