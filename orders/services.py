
from decimal import Decimal

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from admin_panel.models import ProductVariant
from orders.models import Order, OrderItem, OrderStatusHistory
from django.db.models import F
from django.utils import timezone
from orders.models import ReturnRequest


class OrderCancellationError(Exception):
    pass


@transaction.atomic
def cancel_order_items(order_id, item_id=None, reason="",cancelled_by=None):

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
        item.cancelled_by = cancelled_by

    OrderItem.objects.bulk_update(
        items_to_cancel,
        ["status", "cancellation_reason", "cancelled_at","cancelled_by"]
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
            changed_by=cancelled_by
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



@transaction.atomic
def update_order_status(order_id, new_status, changed_by):

    # Lock the order
    order = Order.objects.select_for_update().get(
        pk=order_id
    )

    # Only the immediate next status is allowed
    allowed_transitions = {
        "pending": "shipped",
        "shipped": "out_for_delivery",
        "out_for_delivery": "delivered",
    }

    next_status = allowed_transitions.get(
        order.order_status
    )

    if new_status != next_status:
        raise OrderCancellationError(
            "Invalid status update. "
            "Please follow the correct order tracking sequence."
        )

    # Prevent shipping an order with no active items
    if not OrderItem.objects.filter(
        order=order,
        status="active"
    ).exists():
        raise OrderCancellationError(
            "This order has no active products."
        )


    order.order_status = new_status

    # COD payment is collected upon successful delivery
    if new_status == "delivered" and order.payment_method == "cod":
        order.payment_status = "paid"

    order.save(
        update_fields=[
            "order_status",
            "payment_status",
            "updated_at"
        ]
    )

    # Save tracking history
    OrderStatusHistory.objects.create(
        order=order,
        status=new_status,
        changed_by=changed_by
    )

    return order





class ReturnRequestError(Exception):
    pass


@transaction.atomic
def create_return_request(order_item_id, user, reason):

    reason = reason.strip()

    if not reason:
        raise ReturnRequestError(
            "Please provide a reason for returning this product."
        )

    item = (
        OrderItem.objects
        .select_for_update()
        .select_related("order")
        .get(pk=order_item_id, order__user=user)
    )

    if item.order.order_status != "delivered":
        raise ReturnRequestError(
            "Returns are allowed only for delivered orders."
        )

    if item.status != "active":
        raise ReturnRequestError(
            "This product is not eligible for return."
        )

    if ReturnRequest.objects.filter(order_item=item).exists():
        raise ReturnRequestError(
            "A return request already exists for this product."
        )

    return_request = ReturnRequest.objects.create(
        order_item=item,
        reason=reason,
        status="pending"
    )

    item.status = "return_requested"
    item.save(update_fields=["status"])

    return return_request


@transaction.atomic
def review_return_request(return_request_id, decision):

    if decision not in ("approved", "rejected"):
        raise ReturnRequestError("Invalid return decision.")

    # Lock the order item first to prevent concurrent reviews
    request_item_id = ReturnRequest.objects.values_list(
        "order_item_id", flat=True
    ).get(pk=return_request_id)

    item = OrderItem.objects.select_for_update().get(
        pk=request_item_id
    )

    return_request = ReturnRequest.objects.select_for_update().get(
        pk=return_request_id,
        order_item=item
    )

    if return_request.status != "pending":
        raise ReturnRequestError(
            "This return request has already been reviewed."
        )

    if item.status != "return_requested":
        raise ReturnRequestError(
            "This product is not awaiting return approval."
        )

    if decision == "approved":

        # Restore stock only once, on approval
        ProductVariant.objects.select_for_update().get(
            pk=item.variant_id
        )

        ProductVariant.objects.filter(
            pk=item.variant_id
        ).update(
            stock=F("stock") + item.quantity
        )

        item.status = "returned"

    else:
        # Rejected: product remains with customer
        item.status = "active"

    item.save(update_fields=["status"])

    return_request.status = decision
    return_request.reviewed_at = timezone.now()

    return_request.save(
        update_fields=["status", "reviewed_at"]
    )

    return return_request

