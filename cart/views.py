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
from django.shortcuts import redirect
from django.contrib import messages
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
        # Check latest stock after admin updates
        if variant.stock <= 0:

         return JsonResponse({
          "success": False,
            "stock_unavailable": True,
            "available_stock": 0,
            "message": (
                f"Size UK {variant.size} is unavailable. "
                "Please select another size, move this product "
                "to your wishlist, or remove it to proceed to checkout."
            )
         }, status=400)

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
        # Maximum 4 units when variant stock is below 10
        max_allowed_quantity = (
            min(4, variant.stock)
            if variant.stock < 10
            else variant.stock
        )

        if requested_quantity > max_allowed_quantity:
         return JsonResponse({
         "success": False,
         "message": (
            f"You can add a maximum of {max_allowed_quantity} "
            f"units of UK size {variant.size} to your cart."
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
            # Check maximum quantity including existing cart items
            if new_quantity > max_allowed_quantity:
             return JsonResponse({
              "success": False,
               "message": (
                f"You can add a maximum of {max_allowed_quantity} "
                f"units of UK size {variant.size}. "
                f"You already have {cart_item.quantity} in your cart."
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
    has_invalid_items = any(
        not item.variant.product.is_active
        or not item.variant.product.category.is_active
        or item.variant.stock <= 0
        or item.quantity > item.variant.stock
        or (item.variant.stock < 10 and item.quantity > 4)
        for item in cart_items
    )

    can_checkout = bool(cart_count) and not has_invalid_items
    context = {
        "cart_items": cart_items,
        "cart_count": cart_count,
        "subtotal": subtotal,
        "can_checkout": can_checkout,
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
        .select_related("variant__product__category")
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
    # Check whether any cart variant is out of stock
    has_out_of_stock_items = any(
        item.variant.stock <= 0
        for item in cart_items
    )

    # Also check whether requested quantities exceed stock
    has_insufficient_stock_items = any(
        item.quantity > item.variant.stock
        or (item.variant.stock < 10 and item.quantity > 4)
        for item in cart_items
    )
    # Check whether any product or category is blocked
    has_unavailable_products = any(
        not item.variant.product.is_active
        or not item.variant.product.category.is_active
        for item in cart_items
)
    can_checkout = (
        bool(cart_count)
        and not has_out_of_stock_items
        and not has_insufficient_stock_items
        and not has_unavailable_products
    )
    
    return {
        
        "cart_count": cart_count,
        "subtotal": str(subtotal),
        "has_out_of_stock_items": has_out_of_stock_items,
        "has_insufficient_stock_items": has_insufficient_stock_items,
        "can_checkout": can_checkout,
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

        # Fetch the latest stock from database
        variant = (
            ProductVariant.objects
            .select_for_update()
            .select_related("product__category")
            .get(pk=cart_item.variant_id)
        )

        product = variant.product

        # IMPORTANT: Check stock before increase OR decrease
        if variant.stock <= 0:

            return JsonResponse({
                "success": False,
                "stock_unavailable": True,
                "available_stock": 0,
                "message": (
                    f"Size UK {variant.size} is currently unavailable. "
                    "Please select another size, move this product "
                    "to your wishlist, or remove it from your cart "
                    "to proceed to checkout."
                )
            }, status=400)

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

            # Restrict quantity to 4 when variant stock is below 10
            if variant.stock < 10 and cart_item.quantity >= 4:
                return JsonResponse({
                    "success": False,
                    "message": (
                        f"You can add a maximum of 4 units "
                        f"of UK size {variant.size} to your cart."
                    )
                }, status=400)

            cart_item.quantity += 1

        else:

            if cart_item.quantity <= 1:
                return JsonResponse({
                    "success": False,
                    "message": (
                        "Minimum quantity is 1. "
                        "Use Remove to delete this item."
                    )
                }, status=400)

            cart_item.quantity -= 1

        cart_item.save(
            update_fields=["quantity", "updated_at"]
        )

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
        messages.error(request, "Invalid product size.")
        return redirect("cart:page")

    with transaction.atomic():

        cart_item = get_object_or_404(
            Cart.objects.select_for_update()
            .select_related("variant__product__category"),
            uuid=cart_uuid,
            user=request.user
        )

        product = cart_item.variant.product

        if not product.is_active or not product.category.is_active:
            messages.error(
                request,
                "This product is currently unavailable."
            )
            return redirect("cart:page")

        new_variant = (
            ProductVariant.objects.select_for_update()
            .filter(product=product, size=new_size)
            .first()
        )

        if not new_variant:
            messages.error(
                request,
                "Selected size is unavailable."
            )
            return redirect("cart:page")

        if cart_item.variant_id == new_variant.id:
            return redirect("cart:page")

        existing_item = (
            Cart.objects.select_for_update()
            .filter(user=request.user, variant=new_variant)
            .first()
        )

        combined_quantity = cart_item.quantity

        if existing_item:
            combined_quantity += existing_item.quantity

        if combined_quantity > new_variant.stock:
            messages.error(
                request,
                f"Only {new_variant.stock} units are available "
                f"for UK size {new_size}."
            )
            return redirect("cart:page")
        # Restrict quantity when changing to a low-stock variant
        if new_variant.stock < 10 and combined_quantity > 4:
           messages.error(
                request,
                f"You can add a maximum of 4 units "
                f"of UK size {new_size} to your cart."
            )
           return redirect("cart:page")
        if existing_item:

            existing_item.quantity = combined_quantity
            existing_item.save(
                update_fields=["quantity", "updated_at"]
            )

            cart_item.delete()

        else:

            cart_item.variant = new_variant
            cart_item.save(
                update_fields=["variant", "updated_at"]
            )

    messages.success(
        request,
        "Product size updated successfully."
    )

    return redirect("cart:page")

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
        "cart_count": totals["cart_count"],
        "subtotal": str(totals["subtotal"]),
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