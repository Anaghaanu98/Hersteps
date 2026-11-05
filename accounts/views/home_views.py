from django.shortcuts import render, redirect
from django.db.models import Sum, Prefetch,Q,Max,Min,Exists,OuterRef,Value,IntegerField
from decimal import Decimal, InvalidOperation

from admin_panel.models import Product, Category, ProductVariant,Banner
from decimal import Decimal, InvalidOperation
from django.db.models.functions import Coalesce
from django.db.models import Q, Min, Max
from django.shortcuts import render


def home_view(request):
    # Redirect admin users to the admin dashboard
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect("admin_panel:admin_dashboard")

    # Get newly added active products with available stock
    products = (
        Product.objects
        .filter(
            is_active=True,
            category__is_active=True,
        )
        .annotate(
            available_stock=Sum("variants__stock")
        )
        .filter(
            available_stock__gt=0
        )
        .select_related("category")
        .prefetch_related(
            "images",
            Prefetch(
                "variants",
                queryset=ProductVariant.objects.filter(stock__gt=0),
            ),
        )
        .order_by("-created_at")[:8]
          )
    active_banners = Banner.objects.filter(
    is_active=True
    ).order_by("-created_at", "-pk")[:2]

    context = {
        # Keep all your existing context variables here.
        "products": products,
        # New banner context
        "active_banners": active_banners,
    }
    return render(
        request,
        "accounts/home.html",
        context,
    )



def shop_view(request):

    # -----------------------------------
    # AUTOMATICALLY DISABLE ZERO-STOCK PRODUCTS
    # -----------------------------------

    Product.objects.annotate(
        calculated_stock=Coalesce(
            Sum("variants__stock"),
            Value(0),
            output_field=IntegerField(),
        )
    ).filter(
        calculated_stock__lte=0,
        is_active=True,
    ).update(
        is_active=False
    )

    # -----------------------------------
    # BASE PRODUCTS
    # Show only active products in active categories.
    # Zero-stock products are automatically inactive.
    # -----------------------------------

    products = Product.objects.filter(
        is_active=True,
        category__is_active=True
    ).select_related(
        "category"
    ).prefetch_related(
        "images",
        "variants"
    )

    search_query = request.GET.get("q", "").strip()

    if search_query:
        search_terms = search_query.split()

        for term in search_terms:
            products = products.filter(
                Q(name__icontains=term) |
                Q(description__icontains=term) |
                Q(color__icontains=term) |
                Q(occasion__icontains=term)
            )

    # -----------------------------------
    # CATEGORY FILTER
    # -----------------------------------

    categories = Category.objects.filter(
        is_active=True
    ).order_by("name")

    selected_categories = request.GET.getlist("category")

    if "all" in selected_categories:
        selected_categories = []

    valid_category_ids = list(
        categories.filter(
            pk__in=selected_categories
        ).values_list("pk", flat=True)
    )

    selected_categories = [
        str(category_id) for category_id in valid_category_ids
    ]

    selected_category_name = ""

    if selected_categories:
        products = products.filter(
            category_id__in=selected_categories
        )

        if len(selected_categories) == 1:
            selected_category_name = categories.filter(
                pk=selected_categories[0]
            ).values_list(
                "name",
                flat=True
            ).first() or ""

    # -----------------------------------
    # COLOR FILTER
    # -----------------------------------

    selected_colors = request.GET.getlist("color")

    if selected_colors:
        products = products.filter(
            color__in=selected_colors
        )

    # -----------------------------------
    # SIZE FILTER
    # -----------------------------------

    selected_sizes = request.GET.getlist("size")

    if selected_sizes:
        products = products.filter(
            variants__size__in=selected_sizes
        ).distinct()

    # -----------------------------------
    # OCCASION FILTER
    # -----------------------------------

    selected_occasions = request.GET.getlist("occasion")

    if selected_occasions:
        products = products.filter(
            occasion__in=selected_occasions
        )

    # -----------------------------------
    # PRICE RANGE
    # -----------------------------------

    price_limits = Product.objects.filter(
        is_active=True,
        category__is_active=True
    ).aggregate(
        min_price=Min("price"),
        max_price=Max("price")
    )

    min_available_price = (
        price_limits["min_price"] or Decimal("0")
    )

    max_available_price = (
        price_limits["max_price"] or Decimal("10000")
    )

    def get_valid_price(value, default):
        try:
            price = Decimal(value)

            if not price.is_finite():
                return default

            return max(
                min_available_price,
                min(price, max_available_price)
            )

        except (InvalidOperation, TypeError, ValueError):
            return default

    price_min = request.GET.get("min_price", "").strip()
    price_max = request.GET.get("max_price", "").strip()

    current_min_price = (
        get_valid_price(price_min, min_available_price)
        if price_min else min_available_price
    )

    current_max_price = (
        get_valid_price(price_max, max_available_price)
        if price_max else max_available_price
    )

    if current_min_price > current_max_price:
        current_min_price, current_max_price = (
            current_max_price,
            current_min_price
        )

    products = products.filter(
        price__gte=current_min_price,
        price__lte=current_max_price
    )

    # -----------------------------------
    # SORTING
    # -----------------------------------

    sort_by = request.GET.get("sort", "newest")

    sort_options = {
        "newest": "-created_at",
        "price_low": "price",
        "price_high": "-price",
        "az": "name",
        "za": "-name",
    }

    if sort_by not in sort_options:
        sort_by = "newest"

    products = products.order_by(
        sort_options[sort_by],
        "pk"
    )

    # -----------------------------------
    # CONTEXT
    # -----------------------------------

    context = {
        "products": products,
        "categories": categories,

        "selected_categories": selected_categories,
        "selected_category_name": selected_category_name,

        "selected_colors": selected_colors,
        "selected_sizes": selected_sizes,
        "selected_occasions": selected_occasions,

        "search_query": search_query,
        "sort_by": sort_by,

        "color_choices": Product.ColorChoices.choices,
        "occasion_choices": Product.OccasionChoices.choices,
        "size_choices": ProductVariant.SizeChoices.choices,

        "min_available_price": min_available_price,
        "max_available_price": max_available_price,

        "current_min_price": current_min_price,
        "current_max_price": current_max_price,
    }

    return render(
        request,
        "accounts/product_list.html",
        context
    )
