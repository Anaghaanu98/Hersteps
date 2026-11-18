from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, get_object_or_404, render
from django.views.decorators.http import require_POST

from admin_panel.models import ProductVariant
from cart.models import Cart
from my_accounts.models import Address
from orders.models import Order, OrderItem


class OrderValidationError(Exception):
    pass


@login_required(login_url="login")
@require_POST
def place_order(request):

    try:
        with transaction.atomic():

            # Validate delivery address
            address_mode = request.session.get(
                "checkout_address_mode", "saved"
            )

            address_fields = [
                "full_name", "phone", "house_name",
                "locality", "city", "state", "pincode"
            ]

            saved_address = None

            if address_mode == "saved":

                address_id = request.session.get("checkout_address_id")

                
                if not address_id:
                    default_address = (
                        Address.objects.filter(user=request.user)
                        .order_by("-is_default", "-created_at")
                        .first()
                    )

                    if default_address:
                        address_id = default_address.id

                saved_address = Address.objects.filter(
                    id=address_id,
                    user=request.user
                ).first()

                if not saved_address:
                    raise OrderValidationError(
                        "Please select a valid delivery address."
                    )

                delivery_address = {
                    field: getattr(saved_address, field)
                    for field in address_fields
                }

            elif address_mode == "new":

                delivery_address = request.session.get(
                    "checkout_new_address"
                )

                if not delivery_address or any(
                    not delivery_address.get(field)
                    for field in address_fields
                ):
                    raise OrderValidationError(
                        "Please confirm your delivery address."
                    )

            else:
                raise OrderValidationError(
                    "Please select a delivery address."
                )

            # Lock cart rows
            cart_items = list(
                Cart.objects.select_for_update()
                .filter(user=request.user)
                .order_by("pk")
            )

            if not cart_items:
                raise OrderValidationError("Your cart is empty.")

            # Lock product variants
            variant_ids = [item.variant_id for item in cart_items]

            variants = {
                variant.pk: variant
                for variant in ProductVariant.objects
                .select_for_update()
                .select_related("product", "product__category")
                .filter(pk__in=variant_ids)
                .order_by("pk")
            }

            subtotal = Decimal("0.00")
            order_items_data = []

            # Validate cart and calculate subtotal
            for item in cart_items:

                variant = variants.get(item.variant_id)

                if not variant:
                    raise OrderValidationError(
                        "One of your cart items is unavailable."
                    )

                product = variant.product

                if not product.is_active or not product.category.is_active:
                    raise OrderValidationError(
                        f"{product.name} is currently unavailable."
                    )

                if variant.stock <= 0:
                    raise OrderValidationError(
                        f"{product.name} - UK {variant.size} is out of stock."
                    )

                if item.quantity < 1 or item.quantity > variant.stock:
                    raise OrderValidationError(
                        f"Insufficient stock for {product.name} - UK {variant.size}."
                    )

                if variant.stock < 10 and item.quantity > 4:
                    raise OrderValidationError(
                        f"Maximum 4 units allowed for {product.name} - UK {variant.size}."
                    )

                item_total = product.price * item.quantity
                subtotal += item_total

                order_items_data.append({
                    "product": product,
                    "variant": variant,
                    "product_name": product.name,
                    "size": variant.size,
                    "quantity": item.quantity,
                    "price": product.price,
                    "item_total": item_total,
                })

            # Recalculate totals
            shipping_charge = (
                Decimal("0.00")
                if subtotal >= Decimal("2500.00")
                else Decimal("50.00")
            )

            discount = Decimal("0.00")
            total_amount = subtotal + shipping_charge - discount

            # Optionally save new address
            if (
                address_mode == "new"
                and request.session.get("checkout_save_address", False)
            ):
                address_type = request.session.get(
                    "checkout_address_type", "home"
                )

                if address_type not in ("home", "work"):
                    raise OrderValidationError(
                        "Invalid address type."
                    )

                saved_address = Address.objects.create(
                    user=request.user,
                    address_type=address_type,
                    is_default=False,
                    **delivery_address
                )

            # Create order
            order = Order.objects.create(
                user=request.user,
                address=saved_address,
                **delivery_address,
                subtotal=subtotal,
                discount=discount,
                shipping_charge=shipping_charge,
                total_amount=total_amount,
                payment_method="cod",
                payment_status="pending",
                order_status="placed",
            )

            # Create order items
            OrderItem.objects.bulk_create([
                OrderItem(order=order, **data)
                for data in order_items_data
            ])

            # Deduct stock
            for item in cart_items:
                variant = variants[item.variant_id]
                variant.stock -= item.quantity

            ProductVariant.objects.bulk_update(
                list(variants.values()),
                ["stock"]
            )

            #  Clear cart
            Cart.objects.filter(
                pk__in=[item.pk for item in cart_items],
                user=request.user
            ).delete()

    except OrderValidationError as error:
        messages.error(request, str(error))
        return redirect("orders:checkout")

    # Clear checkout session only after successful transaction
    for key in [
        "checkout_address_id",
        "checkout_address_mode",
        "checkout_new_address",
        "checkout_save_address",
        "checkout_address_type",
    ]:
        request.session.pop(key, None)

    messages.success(request, "Your order has been placed successfully!")

    return redirect(
        "orders:order_success",
        order_uuid=order.order_id
    )


@login_required(login_url="login")
def order_success(request, order_uuid):

    order = get_object_or_404(
        Order.objects.prefetch_related("items"),
        order_id=order_uuid,
        user=request.user
    )

    return render(
        request,
        "orders/order_success.html",
        {"order": order}
    )