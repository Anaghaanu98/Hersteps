from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q,Sum,Value
from django.core.paginator import Paginator
from django.db import transaction
from admin_panel.models import Product,ProductImage,ProductVariant
from admin_panel.decorators import admin_required
from django.db.models.functions import Coalesce
from admin_panel.forms import ProductForm
from django.views.decorators.http import require_POST
from urllib.parse import urlencode
from django.db import transaction
from django.urls import reverse



@admin_required
def products_list(request):
    search_query = request.GET.get("q", "").strip()

    products = (
        Product.objects
        .select_related("category")
        .annotate(
            calculated_total_stock=Coalesce(
                Sum("variants__stock"),
                Value(0),
            )
        )
        .order_by("-created_at")
    )

    if search_query:
        products = products.filter(
            Q(uuid__icontains=search_query)
            | Q(name__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    paginator = Paginator(products, 5)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "products": page_obj,
        "search_query": search_query,
    }

    return render(
        request,
        "admin_panel/products_list.html",
        context,
    )
@admin_required
def add_product(request):

    if request.method == "POST":

        form = ProductForm(request.POST)
        images = request.FILES.getlist("images")

        if len(images) > 4:
            form.add_error(
                None,
                "You can upload a maximum of 4 images."
            )

        for image in images:

            if image.content_type not in [
                "image/jpeg",
                "image/png",
                "image/webp"
            ]:
                form.add_error(
                    None,
                    "Only JPG, PNG and WEBP images are allowed."
                )
                break

            if image.size > 5 * 1024 * 1024:
                form.add_error(
                    None,
                    "Each image must be smaller than 5 MB."
                )
                break

        if form.is_valid():

            if not images:
                form.add_error(
                    None,
                    "Please upload at least one product image."
                )

            if not form.errors:

                with transaction.atomic():

                    product = form.save()

                    for image in images:
                        ProductImage.objects.create(
                            product=product,
                            image=image
                        )

                messages.success(
                    request,
                    "Product details added successfully. Now add sizes."
                )

                return redirect(
                    "admin_panel:add_product_variants",
                    product_id=product.id
                )

    else:
        form = ProductForm()

    return render(
        request,
        "admin_panel/add_products.html",
        {"form": form}
    )


@admin_required
def add_product_variants(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    available_sizes = ProductVariant.SizeChoices.choices

    # existing_stock = {
    #     variant.size: variant.stock
    #     for variant in product.variants.all()
    # }   

    # existing_sizes = set(existing_stock.keys())

    if request.method == "POST":
        selected_sizes = request.POST.getlist("sizes")

        valid_sizes = {
            value for value, label in available_sizes
        }

        if not selected_sizes:
            messages.error(
                request,
                "Please select at least one size."
            )

        elif (
            len(selected_sizes) != len(set(selected_sizes))
            or not set(selected_sizes).issubset(valid_sizes)
        ):
            messages.error(
                request,
                "Invalid size selection."
            )

        else:
            stock_data = {}
            errors = []

            for size in selected_sizes:
                stock_value = request.POST.get(
                    f"stock_{size}", ""
                ).strip()

                try:
                    stock = int(stock_value)

                    if stock < 0:
                        raise ValueError

                    stock_data[size] = stock

                except (ValueError, TypeError):
                    errors.append(
                        f"Enter a valid non-negative stock "
                        f"quantity for UK {size}."
                    )

            if errors:
                for error in errors:
                    messages.error(request, error)

            else:
                with transaction.atomic():
                    for size, stock in stock_data.items():
                        ProductVariant.objects.update_or_create(
                            product=product,
                            size=size,
                            defaults={"stock": stock},
                        )

                messages.success(
                    request,
                    "Product sizes and stock updated successfully."
                )

                return redirect("admin_panel:products_list")

        
        if request.method == "POST":
            existing_sizes = set(selected_sizes)

            for size in selected_sizes:
                stock_value = request.POST.get(
                    f"stock_{size}", ""
                ).strip()

                try:
                    existing_stock[size] = int(stock_value)
                except (ValueError, TypeError):
                    existing_stock[size] = stock_value

    size_rows = [
        {
            "value": value,
            "label": label,
            "stock": existing_stock.get(value, 0),
        }
        for value, label in available_sizes
    ]

    return render(
        request,
        "admin_panel/add_product_variants.html",
        {
            "product": product,
            "product_uuid": product.uuid,
            "size_rows": size_rows,
            "existing_sizes": existing_sizes,
        },
    )

@admin_required
def edit_product(request, product_uuid):
    product = get_object_or_404(Product, uuid=product_uuid)

   
    return_page = (
        request.POST.get("return_page", "1")
        if request.method == "POST"
        else request.GET.get("page", "1")
    )

    
    if not return_page.isdigit() or int(return_page) < 1:
        return_page = "1"

    existing_images = product.images.all()

    if request.method == "POST":
        form = ProductForm(request.POST, instance=product)

        new_images = request.FILES.getlist("images")
        delete_image_ids = request.POST.getlist("delete_images")

        images_to_delete = product.images.filter(
            id__in=delete_image_ids
        )

        remaining_count = (
            existing_images.count() - images_to_delete.count()
        )
        total_count = remaining_count + len(new_images)

        if total_count > 4:
            form.add_error(
                None,
                "A product can have a maximum of 4 images."
            )

        for image in new_images:
            if image.content_type not in [
                "image/jpeg",
                "image/png",
                "image/webp",
            ]:
                form.add_error(
                    None,
                    "Only JPG, PNG and WEBP images are allowed."
                )
                break

            if image.size > 5 * 1024 * 1024:
                form.add_error(
                    None,
                    "Each image must be smaller than 5 MB."
                )
                break

        if form.is_valid():
            if total_count == 0:
                form.add_error(
                    None,
                    "A product must have at least one image."
                )

            if not form.errors:
                with transaction.atomic():
                    form.save()

                    images_to_delete.delete()

                    for image in new_images:
                        ProductImage.objects.create(
                            product=product,
                            image=image
                        )

                messages.success(
                    request,
                    "Product updated successfully."
                )

                variants_url = reverse(
                    "admin_panel:edit_product_variants",
                    kwargs={"product_uuid": product.uuid},
                )

                return redirect(
                    f"{variants_url}?{urlencode({'page': return_page})}"
                )

    else:
        form = ProductForm(instance=product)

    return render(
        request,
        "admin_panel/edit_product.html",
        {
            "form": form,
            "product": product,
            "existing_images": existing_images,
            "return_page": return_page,
        }
    )

@admin_required
def edit_product_variants(request, product_uuid):
    product = get_object_or_404(Product, uuid=product_uuid)

    available_sizes = ProductVariant.SizeChoices.choices
    valid_sizes = {value for value, label in available_sizes}

    if request.method == "POST":
        selected_sizes = request.POST.getlist("sizes")

        if (
            len(selected_sizes) != len(set(selected_sizes))
            or not set(selected_sizes).issubset(valid_sizes)
        ):
            messages.error(request, "Invalid size selection.")
        else:
            stock_data = {}
            errors = []

            for size in selected_sizes:
                stock_value = request.POST.get(
                    f"stock_{size}", ""
                ).strip()

                try:
                    stock = int(stock_value)

                    if stock < 0:
                        raise ValueError

                    stock_data[size] = stock

                except (ValueError, TypeError):
                    errors.append(
                        f"Enter a valid stock quantity for UK {size}."
                    )

            if errors:
                for error in errors:
                    messages.error(request, error)

            else:
                with transaction.atomic():
                   
                    for size, stock in stock_data.items():
                        ProductVariant.objects.update_or_create(
                            product=product,
                            size=size,
                            defaults={"stock": stock},
                        )

                    # Remove variants that were unchecked.
                    product.variants.exclude(
                        size__in=selected_sizes
                    ).delete()

                messages.success(
                    request,
                    "Product variants and stock updated successfully.",
                )

                return_page = request.POST.get("return_page", "1")

                if not return_page.isdigit() or int(return_page) < 1:
                    return_page = "1"

                products_url = reverse("admin_panel:products_list")

                return redirect(
    f"{products_url}?{urlencode({'page': return_page})}"
)

    existing_stock = {
        variant.size: variant.stock
        for variant in product.variants.all()
    }

    size_rows = [
        {
            "value": value,
            "label": label,
            "stock": existing_stock.get(value, 0),
            "exists": value in existing_stock,
        }
        for value, label in available_sizes
    ]

    return render(
        request,
        "admin_panel/edit_product_variant.html",
        {
            "product": product,
            "size_rows": size_rows,
        },
    )



@admin_required
@require_POST
def toggle_product_status(request, product_uuid):

    if request.method != "POST":
        return redirect("admin_panel:products_list")

    product = get_object_or_404(
        Product,
        uuid=product_uuid
    )

   
    total_stock = product.variants.aggregate(
        total=Sum("stock")
    )["total"] or 0

    if total_stock <= 0:
        product.is_active = False
        product.save(update_fields=["is_active", "updated_at"])

        messages.warning(
            request,
            f"{product.name} cannot be activated because it has no stock."
        )

    else:
        # Toggle product status
        product.is_active = not product.is_active

        product.save(update_fields=["is_active", "updated_at"])

        if product.is_active:
            messages.success(
                request,
                f"{product.name} has been activated."
            )
        else:
            messages.success(
                request,
                f"{product.name} has been blocked."
            )

   
    page = request.GET.get("page", "1")
    search_query = request.GET.get("q", "")

    url = reverse("admin_panel:products_list")

    query_params = urlencode({
        "page": page,
        "q": search_query,
    })

    return redirect(f"{url}?{query_params}")