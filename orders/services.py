
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from admin_panel.models import ProductVariant
from orders.models import Order, OrderItem, OrderStatusHistory


class OrderCancellationError(Exception):
    pass


@transaction.atomic
def cancel_order_items(order_id, item_id=None, reason=""):

    # Lock the order to prevent simultaneous cancellation
    order = Order.objects.select_for_update().get(pk=order_id)

    # Cancellation is allowed only before shipping
    if order.order_status != "pending":
        raise OrderCancellationError(
            "This order can no longer be cancelled."
        )

    # Lock all order items
    order_items = list(
        OrderItem.objects.select_for_update()
        .filter(order=order)
        .order_by("pk")
    )

    if item_id is not None:
        items_to_cancel = [
            item for item in order_items
            if item.pk == item_id
        ]

        if not items_to_cancel:
            raise OrderCancellationError(
                "Order item not found."
            )
    else:
        items_to_cancel = [
            item for item in order_items
            if item.status == "active"
        ]

    if not items_to_cancel:
        raise OrderCancellationError(
            "No active items available for cancellation."
        )

    # Prevent duplicate stock increments
    for item in items_to_cancel:
        if item.status != "active":
            raise OrderCancellationError(
                "This product has already been cancelled."
            )

    # Existing checkout currently has no discounts.
    # Prevent incorrect recalculation if discounts are added.
    if order.discount != Decimal("0.00"):
        raise OrderCancellationError(
            "Cancellation requires a discount adjustment."
        )

    # Lock variants in a consistent order
    variant_ids = sorted({
        item.variant_id for item in items_to_cancel
    })

    variants = {
        variant.pk: variant
        for variant in ProductVariant.objects
        .select_for_update()
        .filter(pk__in=variant_ids)
        .order_by("pk")
    }

    if len(variants) != len(variant_ids):
        raise OrderCancellationError(
            "A product variant is unavailable."
        )

    # Restore stock and mark items cancelled
    for item in items_to_cancel:

        ProductVariant.objects.filter(
            pk=item.variant_id
        ).update(
            stock=F("stock") + item.quantity
        )

        item.status = "cancelled"
        item.cancellation_reason = reason
        item.cancelled_at = timezone.now()

    OrderItem.objects.bulk_update(
        items_to_cancel,
        ["status", "cancellation_reason", "cancelled_at"]
    )

    # Calculate subtotal from remaining active items
    remaining_items = [
        item for item in order_items
        if item.status == "active"
    ]

    subtotal = sum(
        (item.item_total for item in remaining_items),
        Decimal("0.00")
    )

    if not remaining_items:
        shipping_charge = Decimal("0.00")
        order.order_status = "cancelled"

        OrderStatusHistory.objects.create(
            order=order,
            status="cancelled",
            changed_by=None
        )

    else:
        shipping_charge = (
            Decimal("0.00")
            if subtotal >= Decimal("2500.00")
            else Decimal("50.00")
        )

    order.subtotal = subtotal
    order.shipping_charge = shipping_charge
    order.total_amount = (
        subtotal + shipping_charge - order.discount
    )

    order.save(
        update_fields=[
            "subtotal",
            "shipping_charge",
            "total_amount",
            "order_status",
            "updated_at"
        ]
    )

    return order

