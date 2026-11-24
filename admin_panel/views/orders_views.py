
import uuid

from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render

from orders.models import Order
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from orders.services import (cancel_order_items,update_order_status,OrderCancellationError)
from admin_panel.decorators import admin_required


@admin_required
def order_list(request):

    orders = (
        Order.objects
        .select_related("user")
        .order_by("-created_at", "-pk")
    )

    # Search
    search_query = request.GET.get("q", "").strip()

    if search_query:

        filters = (
            Q(order_id__icontains=search_query)
            |Q(full_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(user__username__icontains=search_query)
            | Q(phone__icontains=search_query)
        )

        try:
            order_uuid = uuid.UUID(search_query)
            filters |= Q(order_id=order_uuid)
        except (ValueError, AttributeError):
            pass

        orders = orders.filter(filters)

    # Status filter
    selected_status = request.GET.get("status", "")

    valid_statuses = [
        choice[0] for choice in Order.ORDER_STATUS
    ]

    if selected_status in valid_statuses:
        orders = orders.filter(
            order_status=selected_status
        )
    else:
        selected_status = ""

    # Payment method filter
    selected_payment = request.GET.get("payment", "").strip().lower()

    valid_payment_methods = ["wallet", "razorpay", "cod"]

    if selected_payment in valid_payment_methods:
        orders = orders.filter(
            payment_method=selected_payment
        )
    else:
        selected_payment = ""

    # Sorting
    selected_sort = request.GET.get(
            "sort", "newest"
        )

    sort_options = {
        "newest": ("-created_at", "-pk"),
        "oldest": ("created_at", "pk"),
        "amount_high": ("-total_amount", "-pk"),
        "amount_low": ("total_amount", "pk"),
    }

    if selected_sort not in sort_options:
        selected_sort = "newest"

    orders = orders.order_by(
        *sort_options[selected_sort]
    )

    # Pagination
    paginator = Paginator(orders, 10)

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "admin_panel/order_list.html",
        {
            "orders": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "selected_status": selected_status,
            "selected_sort": selected_sort,
            "status_choices": Order.ORDER_STATUS,
            "selected_payment": selected_payment,
        }
    )


@admin_required
def admin_order_detail(request, order_uuid):

    order = get_object_or_404(
        Order.objects
        .select_related("user")
        .prefetch_related(
            "items__product__images",
            "status_history__changed_by",
            "items__cancelled_by",
        ),
        order_id=order_uuid
    )

    status_transitions = {
        "pending": "shipped",
        "shipped": "out_for_delivery",
        "out_for_delivery": "delivered",
    }

    next_status = status_transitions.get(
        order.order_status
    )

    can_cancel = (
        order.order_status == "pending"
        and order.items.filter(
            status="active"
        ).exists()
    )
    has_cancelled_items = order.items.filter(
    status="cancelled"
   ).exists()
    return render(
        request,
        "admin_panel/order_detail.html",
        {
            "order": order,
            "next_status": next_status,
            "can_cancel": can_cancel,
            "status_choices": Order.ORDER_STATUS,
            "has_cancelled_items": has_cancelled_items,
        }
    )


@admin_required
@require_POST
def admin_update_order_status(request, order_uuid):

    order = get_object_or_404(
        Order,
        order_id=order_uuid
    )

    new_status = request.POST.get(
        "order_status", ""
    )

    try:
        update_order_status(
            order_id=order.pk,
            new_status=new_status,
            changed_by=request.user
        )

        messages.success(
            request,
            "Order status updated successfully."
        )

    except OrderCancellationError as error:
        messages.error(request, str(error))

    return redirect(
        "admin_panel:order_detail",
        order_uuid=order_uuid
    )


@admin_required
@require_POST
def admin_cancel_order(request, order_uuid):

    order = get_object_or_404(
        Order,
        order_id=order_uuid
    )

    reason = request.POST.get(
        "cancellation_reason", ""
    ).strip()

    try:
        cancel_order_items(
            order_id=order.pk,
            reason=reason,
            cancelled_by=request.user
)

        messages.success(
            request,
            "Order cancelled successfully. "
            "Stock has been restored."
        )

    except OrderCancellationError as error:
        messages.error(request, str(error))

    return redirect(
        "admin_panel:order_detail",
        order_uuid=order_uuid
    )


@admin_required
@require_POST
def admin_cancel_order_item(request, order_uuid, item_id):

    order = get_object_or_404(
        Order,
        order_id=order_uuid
    )

    reason = request.POST.get(
        "cancellation_reason", ""
    ).strip()

    try:
        cancel_order_items(
            order_id=order.pk,
            item_id=item_id,
            reason=reason,
            cancelled_by=request.user
        )

        messages.success(
            request,
            "Product cancelled successfully. Stock has been restored."
        )

    except OrderCancellationError as error:
        messages.error(request, str(error))

    return redirect(
        "admin_panel:order_detail",
        order_uuid=order_uuid
    )
