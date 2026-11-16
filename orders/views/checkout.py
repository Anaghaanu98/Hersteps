
from decimal import Decimal
from orders.forms import CheckoutAddressForm
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from cart.models import Cart
from my_accounts.models import Address


@login_required(login_url="login")
def checkout_view(request):

    # FETCH USER CART ITEMS

    cart_items = list(
        Cart.objects.filter(
            user=request.user
        )
        .select_related(
            "variant",
            "variant__product",
            "variant__product__category"
        )
        .prefetch_related(
            "variant__product__images"
        )
        .order_by("-created_at")
    )

    # PREVENT CHECKOUT WITH EMPTY CART

    if not cart_items:
        messages.error(
            request,
            "Your cart is empty. Please add products before checkout."
        )
        return redirect("cart:page")

    # VALIDATE PRODUCTS AND STOCK

    for item in cart_items:

        variant = item.variant
        product = variant.product

        if not product.is_active or not product.category.is_active:
            messages.error(
                request,
                f"{product.name} is currently unavailable."
            )
            return redirect("cart:page")

        if variant.stock <= 0:
            messages.error(
                request,
                f"{product.name} - UK {variant.size} is out of stock."
            )
            return redirect("cart:page")

        if item.quantity > variant.stock:
            messages.error(
                request,
                f"Only {variant.stock} units of "
                f"{product.name} - UK {variant.size} are available."
            )
            return redirect("cart:page")

        # Maintain existing cart quantity restriction
        if variant.stock < 10 and item.quantity > 4:
            messages.error(
                request,
                f"Maximum 4 units allowed for "
                f"{product.name} - UK {variant.size}."
            )
            return redirect("cart:page")

        # Calculate individual item total
        item.item_total = (
            product.price * item.quantity
        )

    # CALCULATE SUBTOTAL

    subtotal = sum(
        (item.item_total for item in cart_items),
        Decimal("0.00")
    )

    # SHIPPING CALCULATION

    if subtotal >= Decimal("2500.00"):
        shipping_charge = Decimal("0.00")
    else:
        shipping_charge = Decimal("50.00")

    # Coupon functionality will be implemented later
    discount = Decimal("0.00")

    # FINAL PAYABLE AMOUNT

    total_amount = (
        subtotal + shipping_charge - discount
    )

    # FETCH USER ADDRESSES

    addresses = list(
        Address.objects.filter(
            user=request.user
        ).order_by("-is_default", "-created_at")
    )

    
    # SELECT DEFAULT ADDRESS

    default_address = next(
        (address for address in addresses if address.is_default),
        addresses[0] if addresses else None
    )

    valid_address_ids = {address.id for address in addresses}

    selected_address_id = request.session.get("checkout_address_id")

    if selected_address_id not in valid_address_ids:
        selected_address_id = (
            default_address.id if default_address else None
        )

    address_mode = request.session.get("checkout_address_mode", "saved")

    if not addresses and address_mode == "saved":
        address_mode = "new"

    # Store the selected saved address in the session
    if address_mode == "saved" and selected_address_id:
        request.session["checkout_address_id"] = selected_address_id

    saved_new_address = request.session.get("checkout_new_address", {})

    save_address = request.session.get("checkout_save_address", False)

    new_address_type = request.session.get("checkout_address_type", "home")

    checkout_address_form = CheckoutAddressForm(
        initial=saved_new_address
    )
    # HANDLE DELIVERY ADDRESS SELECTION

    if request.method == "POST":

     action = request.POST.get("action")
        # SELECT PREVIOUSLY CONFIRMED NEW ADDRESS

     if action == "select_new":

        new_address = request.session.get("checkout_new_address")

        if not new_address:
           messages.error(
              request,
              "Please enter and confirm a delivery address."
         )
           return redirect("orders:checkout")

        request.session["checkout_address_mode"] = "new"

        return redirect("orders:checkout")
        # SELECT EXISTING SAVED ADDRESS
      
     elif action == "select_saved":

            try:
                requested_address_id = int(
                    request.POST.get("address_id", "")
                )
            except (TypeError, ValueError):
                messages.error(request, "Please select a valid address.")
                return redirect("orders:checkout")

            if requested_address_id not in valid_address_ids:
                messages.error(
                    request,
                    "Selected address is unavailable."
                )
                return redirect("orders:checkout")

            request.session["checkout_address_id"] = requested_address_id
            request.session["checkout_address_mode"] = "saved"

            return redirect("orders:checkout")

        # VALIDATE NEW DELIVERY ADDRESS

     elif action == "save_new_address":

            address_mode = "new"

            request.session["checkout_address_mode"] = "new"

            # Clear previously confirmed address only when
            # submitting a new address for validation
            request.session.pop("checkout_new_address", None)

            saved_new_address = {}

            checkout_address_form = CheckoutAddressForm(
                request.POST
            )

            save_address = request.POST.get("save_address") == "1"
            new_address_type = request.POST.get("address_type", "home")

            address_type_valid = (
                not save_address
                or new_address_type in ("home", "work")
            )

            if checkout_address_form.is_valid() and address_type_valid:

                # Store temporarily in session.
                # Do not create an Address or Order record yet.

                request.session["checkout_new_address"] = {
                    field: checkout_address_form.cleaned_data[field]
                    for field in [
                        "full_name",
                        "phone",
                        "house_name",
                        "locality",
                        "city",
                        "state",
                        "pincode",
                    ]
                }

                request.session["checkout_address_mode"] = "new"
                request.session["checkout_save_address"] = save_address
                request.session["checkout_address_type"] = new_address_type

                messages.success(
                    request,
                    "Delivery address confirmed."
                )

                return redirect("orders:checkout")

            if not address_type_valid:
                messages.error(
                    request,
                    "Please select a valid address type."
                )

            messages.error(
                request,
                "Please correct the delivery address details."
            )

    # PREPARE CONTEXT

    context = {
        "cart_items": cart_items,
        "addresses": addresses,
        "default_address": default_address,
        "selected_address_id": selected_address_id,
        "subtotal": subtotal,
        "shipping_charge": shipping_charge,
        "discount": discount,
        "total_amount": total_amount,
        "payment_method": "cod",
        "coupon_enabled": False,
        "checkout_address_form": checkout_address_form,
        "address_mode": address_mode,
        "save_address": save_address,
        "new_address_type": new_address_type,
        "new_address_confirmed": bool(saved_new_address),
        "new_delivery_address": saved_new_address,
    }

    return render(
        request,
        "orders/checkout.html",
        context
    )

