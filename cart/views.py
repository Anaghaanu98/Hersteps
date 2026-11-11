from django.shortcuts import render
import uuid
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Sum
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_GET
from admin_panel.models import ProductVariant
from wishlist.models import Wishlist
from .models import Cart
from django.shortcuts import get_object_or_404

from wishlist.models import Wishlist




@login_required(login_url="login")
@require_POST
def add_to_cart(request):

    product_uuid = request.POST.get("product_uuid")
    size = request.POST.get("size")

    # Default to 1 for existing wishlist functionality
    quantity_value = request.POST.get("quantity", "1")

    # Validate required fields
    if not product_uuid or not size:
        return JsonResponse({
            "success": False,
            "message": "Please select a product size."
        }, status=400)

    # Validate quantity
    try:
        requested_quantity = int(quantity_value)
    except (ValueError, TypeError):
        return JsonResponse({
            "success": False,
            "message": "Invalid quantity."
        }, status=400)

    if requested_quantity < 1:
        return JsonResponse({
            "success": False,
            "message": "Quantity must be at least 1."
        }, status=400)

    # Validate product UUID
    try:
        product_uuid = uuid.UUID(product_uuid)
    except (ValueError, TypeError, AttributeError):
        return JsonResponse({
            "success": False,
            "message": "Invalid product."
        }, status=400)

    # Validate selected size
    valid_sizes = ProductVariant.SizeChoices.values

    if size not in valid_sizes:
        return JsonResponse({
            "success": False,
            "message": "Invalid product size."
        }, status=400)

    with transaction.atomic():

        # Lock variant to prevent concurrent cart updates
        variant = (
            ProductVariant.objects
            .select_related("product__category")
            .select_for_update()
            .filter(
                product__uuid=product_uuid,
                size=size
            )
            .first()
        )

        if not variant:
            return JsonResponse({
                "success": False,
                "message": "Selected size is unavailable."
            }, status=404)

        product = variant.product

        # Check blocked products/categories
        if (
            not product.is_active
            or not product.category.is_active
        ):
            return JsonResponse({
                "success": False,
                "message": "This product is currently unavailable."
            }, status=403)

        # Check variant stock
        if variant.stock <= 0:
            return JsonResponse({
                "success": False,
                "message": "Selected size is out of stock."
            }, status=400)

        # Check requested quantity against available stock
        if requested_quantity > variant.stock:
            return JsonResponse({
                "success": False,
                "message": (
                    f"Only {variant.stock} units are available "
                    "in this size."
                )
            }, status=400)

        # Add variant to cart
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            variant=variant,
            defaults={"quantity": requested_quantity}
        )

        if not created:

            # Lock existing cart item
            cart_item = (
                Cart.objects
                .select_for_update()
                .get(pk=cart_item.pk)
            )

            # Existing quantity + newly requested quantity
            new_quantity = (
                cart_item.quantity + requested_quantity
            )

            # Prevent total cart quantity exceeding stock
            if new_quantity > variant.stock:
                return JsonResponse({
                    "success": False,
                    "message": (
                        f"Maximum available stock is "
                        f"{variant.stock}. You already have "
                        f"{cart_item.quantity} in your cart."
                    )
                }, status=400)

            Cart.objects.filter(
                pk=cart_item.pk
            ).update(
                quantity=F("quantity") + requested_quantity
            )

        # Remove from wishlist only after successful cart addition
        Wishlist.objects.filter(
            user=request.user,
            product=product
        ).delete()

        # Calculate updated cart quantity
        cart_count = (
            Cart.objects
            .filter(user=request.user)
            .aggregate(total=Sum("quantity"))["total"]
            or 0
        )

        # Calculate updated wishlist count
        wishlist_count = Wishlist.objects.filter(
            user=request.user
        ).count()

    return JsonResponse({
        "success": True,
        "message": "Product added to cart successfully.",
        "product_uuid": str(product.uuid),
        "cart_count": cart_count,
        "wishlist_count": wishlist_count
    })


@require_GET
def cart_count(request):

    if not request.user.is_authenticated:
        return JsonResponse({
            "success": True,
            "count": 0
        })

    count = (
        Cart.objects
        .filter(user=request.user)
        .aggregate(total=Sum("quantity"))["total"]
        or 0
    )

    return JsonResponse({
        "success": True,
        "count": count
    })

@login_required(login_url="login")
def cart_page(request):

    cart_items = (
        Cart.objects
        .filter(user=request.user)
        .select_related(
            "variant",
            "variant__product",
            "variant__product__category"
        )
        .prefetch_related(
            "variant__product__images",
            "variant__product__variants"
        )
        .order_by("-created_at")
    )

    subtotal = sum(
        (
            item.variant.product.price * item.quantity
            for item in cart_items
        ),
        Decimal("0.00")
    )

    cart_count = sum(
        item.quantity
        for item in cart_items
    )

    context = {
        "cart_items": cart_items,
        "cart_count": cart_count,
        "subtotal": subtotal,
    }

    return render(
        request,
        "cart/cart.html",
        context
    )

def get_cart_totals(user):

    cart_items = (
        Cart.objects
        .filter(user=user)
        .select_related("variant__product")
    )

    subtotal = sum(
        (
            item.variant.product.price * item.quantity
            for item in cart_items
        ),
        Decimal("0.00")
    )

    cart_count = sum(
        item.quantity
        for item in cart_items
    )

    return {
        "cart_count": cart_count,
        "subtotal": str(subtotal),
    }


@login_required(login_url="login")
@require_POST
def update_cart_quantity(request):

    cart_uuid = request.POST.get("cart_uuid")
    action = request.POST.get("action")

    if action not in ("increase", "decrease"):
        return JsonResponse({
            "success": False,
            "message": "Invalid quantity action."
        }, status=400)

    with transaction.atomic():

        cart_item = get_object_or_404(
            Cart.objects.select_for_update()
            .select_related("variant__product__category"),
            uuid=cart_uuid,
            user=request.user
        )

        variant = ProductVariant.objects.select_for_update().get(
            pk=cart_item.variant_id
        )

        product = variant.product

        if not product.is_active or not product.category.is_active:
            return JsonResponse({
                "success": False,
                "message": "This product is currently unavailable."
            }, status=403)

        if action == "increase":

            if cart_item.quantity >= variant.stock:
                return JsonResponse({
                    "success": False,
                    "message": "Maximum available stock reached."
                }, status=400)

            cart_item.quantity += 1

        else:

            if cart_item.quantity <= 1:
                return JsonResponse({
                    "success": False,
                    "message": "Minimum quantity is 1. Use Remove to delete this item."
                }, status=400)

            cart_item.quantity -= 1

        cart_item.save(update_fields=["quantity", "updated_at"])

        totals = get_cart_totals(request.user)

    return JsonResponse({
        "success": True,
        "message": "Cart quantity updated.",
        "quantity": cart_item.quantity,
        **totals
    })


@login_required(login_url="login")
@require_POST
def change_cart_size(request):

    cart_uuid = request.POST.get("cart_uuid")
    new_size = request.POST.get("size")

    if new_size not in ProductVariant.SizeChoices.values:
        return JsonResponse({
            "success": False,
            "message": "Invalid product size."
        }, status=400)

    with transaction.atomic():

        cart_item = get_object_or_404(
            Cart.objects.select_for_update()
            .select_related("variant__product__category"),
            uuid=cart_uuid,
            user=request.user
        )

        product = cart_item.variant.product

        if not product.is_active or not product.category.is_active:
            return JsonResponse({
                "success": False,
                "message": "This product is currently unavailable."
            }, status=403)

        new_variant = (
            ProductVariant.objects.select_for_update()
            .filter(product=product, size=new_size)
            .first()
        )

        if not new_variant:
            return JsonResponse({
                "success": False,
                "message": "Selected size is unavailable."
            }, status=404)

        if cart_item.variant_id == new_variant.id:
            return JsonResponse({
                "success": True,
                "message": "Size unchanged.",
                "merged": False,
                "quantity": cart_item.quantity,
                **get_cart_totals(request.user)
            })

        existing_item = (
            Cart.objects.select_for_update()
            .filter(user=request.user, variant=new_variant)
            .first()
        )

        combined_quantity = cart_item.quantity

        if existing_item:
            combined_quantity += existing_item.quantity

        if combined_quantity > new_variant.stock:
            return JsonResponse({
                "success": False,
                "message": (
                    f"Only {new_variant.stock} units are available "
                    f"for UK size {new_size}."
                )
            }, status=400)

        if existing_item:

            existing_item.quantity = combined_quantity
            existing_item.save(
                update_fields=["quantity", "updated_at"]
            )

            cart_item.delete()
            merged = True

        else:

            cart_item.variant = new_variant
            cart_item.save(
                update_fields=["variant", "updated_at"]
            )

            merged = False

        totals = get_cart_totals(request.user)

    return JsonResponse({
        "success": True,
        "message": "Product size updated.",
        "merged": merged,
        "quantity": combined_quantity,
        "size": new_size,
        **totals,
        "cart_uuid": str(cart_item.uuid),
        "target_cart_uuid": str(existing_item.uuid) if existing_item else None
    })

@login_required(login_url="login")
@require_POST
def remove_cart_item(request):

    cart_uuid = request.POST.get("cart_uuid")

    with transaction.atomic():

        cart_item = get_object_or_404(
            Cart.objects.select_for_update(),
            uuid=cart_uuid,
            user=request.user
        )

        cart_item.delete()

        totals = get_cart_totals(request.user)

    return JsonResponse({
        "success": True,
        "message": "Product removed from cart.",
        **totals
    })

@login_required(login_url="login")
@require_POST
def move_to_wishlist(request):

    cart_uuid = request.POST.get("cart_uuid")

    if not cart_uuid:
        return JsonResponse({
            "success": False,
            "message": "Cart item is required."
        }, status=400)

    with transaction.atomic():

        cart_item = (
            Cart.objects
            .select_for_update()
            .select_related("variant__product__category")
            .filter(
                uuid=cart_uuid,
                user=request.user
            )
            .first()
        )

        if not cart_item:
            return JsonResponse({
                "success": False,
                "message": "Cart item not found."
            }, status=404)

        product = cart_item.variant.product

        # Maintain the same product availability rule
        # used in your existing wishlist toggle.
        if not product.is_active or not product.category.is_active:
            return JsonResponse({
                "success": False,
                "message": "This product is currently unavailable."
            }, status=403)

        # Avoid duplicate wishlist entries
        Wishlist.objects.get_or_create(
            user=request.user,
            product=product
        )

        # Remove the selected cart entry only after
        # the wishlist operation succeeds.
        cart_item.delete()

        totals = get_cart_totals(request.user)

        wishlist_count = Wishlist.objects.filter(
            user=request.user
        ).count()

    return JsonResponse({
        "success": True,
        "message": "Product moved to wishlist successfully.",
        "wishlist_count": wishlist_count,
        **totals
    })