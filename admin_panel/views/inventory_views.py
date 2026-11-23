
from django.core.paginator import Paginator
from django.db.models import Count, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import render
from admin_panel.decorators import admin_required
from admin_panel.models import Category, Product, ProductVariant

# Keep your existing admin_required import here.


@admin_required
def inventory_dashboard(request):
    context = {
        "total_categories": Category.objects.count(),
        "total_products": Product.objects.count(),
        "total_variants": ProductVariant.objects.count(),
        "total_stock": ProductVariant.objects.aggregate(
            total=Coalesce(Sum("stock"), 0)
        )["total"],
        "low_stock_count": ProductVariant.objects.filter(
            stock__gt=0,
            stock__lt=10
        ).count(),
        "out_of_stock_count": ProductVariant.objects.filter(
            stock=0
        ).count(),
    }

    return render(
        request,
        "admin_panel/inventory_dashboard.html",
        context
    )


@admin_required
def inventory_categories(request):
    categories = Category.objects.annotate(
        product_count=Count("products", distinct=True),
        total_stock=Coalesce(
            Sum("products__variants__stock"),
            0
        )
    ).order_by("name")

    return render(
        request,
        "admin_panel/inventory_categories.html",
        {"categories": categories}
    )


@admin_required
def inventory_products(request):
    variants = ProductVariant.objects.select_related(
        "product",
        "product__category"
    ).order_by("product__name", "size", "pk")

    search_query = request.GET.get("q", "").strip()
    stock_filter = request.GET.get("stock", "all")
    size_filter = request.GET.get("size", "all")

    if search_query:
        variants = variants.filter(
            product__name__icontains=search_query
        )

    if stock_filter == "in":
        variants = variants.filter(stock__gte=10)
    elif stock_filter == "low":
        variants = variants.filter(
            stock__gt=0,
            stock__lt=10
        )
    elif stock_filter == "out":
        variants = variants.filter(stock=0)

    size_choices = ProductVariant.SizeChoices.choices
    valid_sizes = [str(value) for value, _ in size_choices]

    if size_filter in valid_sizes:
        variants = variants.filter(size=size_filter)

    paginator = Paginator(variants, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "stock_filter": stock_filter,
        "size_filter": size_filter,
        "size_choices": size_choices,
        "filter_query": query_params.urlencode(),
    }

    return render(
        request,
        "admin_panel/inventory_products.html",
        context
    )
