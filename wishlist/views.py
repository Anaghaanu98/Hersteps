
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.shortcuts import render
from .models import Wishlist
from admin_panel.models import Product
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse


@require_POST
def toggle_wishlist(request):
    # Make sure the user is logged in
    if not request.user.is_authenticated:
        return JsonResponse(
            {"success": False, "message": "Please log in."},
            status=401
        )

    product_id = request.POST.get("product_id")

    
    if not product_id:
        return JsonResponse(
            {"success": False, "message": "Product ID is required."},
            status=400
        )

    try:
        product = Product.objects.get(pk=product_id)
    except (Product.DoesNotExist, ValueError):
        return JsonResponse(
            {"success": False, "message": "Product not found."},
            status=404
        )
    # Check whether product or category is blocked
    if not product.is_active or not product.category.is_active:

     messages.error(
        request,
        "Sorry! This product is currently unavailable."
    )

     return JsonResponse({
        "success": False,
        "message": "Sorry! This product is currently unavailable.",
        "redirect_url": reverse("shop")
     }, status=403)
    wishlist_item = Wishlist.objects.filter(
        user=request.user,
        product=product
    )

    if wishlist_item.exists():
        wishlist_item.delete()
        added = False
    else:
        Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )
        added = True

    # Always calculate the count from the database
    wishlist_count = Wishlist.objects.filter(
        user=request.user
    ).count()

    return JsonResponse({
        "success": True,
        "added": added,
        "count": wishlist_count,
        "product_id": product.id
    })


@require_GET
def wishlist_status(request):
    if not request.user.is_authenticated:
        return JsonResponse({
            "success": True,
            "count": 0,
            "product_ids": []
        })

    product_ids = request.GET.get("product_ids", "")

    # Get wishlist status for products displayed on the current page
    if product_ids:
        try:
            product_id_list = [
                int(product_id)
                for product_id in product_ids.split(",")
                if product_id.strip()
            ]
        except ValueError:
            return JsonResponse(
                {"success": False, "message": "Invalid product IDs."},
                status=400
            )

        wishlisted_ids = list(
            Wishlist.objects.filter(
                user=request.user,
                product_id__in=product_id_list
            ).values_list("product_id", flat=True)
        )
    else:
        wishlisted_ids = []

    wishlist_count = Wishlist.objects.filter(
        user=request.user
    ).count()

    return JsonResponse({
        "success": True,
        "count": wishlist_count,
        "product_ids": wishlisted_ids
    })

@login_required(login_url="login")
def wishlist_page(request):
    wishlist_items = (
        Wishlist.objects
        .filter(user=request.user)
        .select_related("product", "product__category")
        .prefetch_related("product__images")
    )

    return render(request, "wishlist/wishlist.html", {
        "wishlist_items": wishlist_items
    })
# Create your views here.
