from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.shortcuts import redirect,get_object_or_404
from orders.models import Order
from orders.services import (cancel_order_items, OrderCancellationError)
from django.contrib import messages
from django.views.decorators.http import require_POST


@login_required(login_url="login")
def order_list(request):

    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "orders/order_list.html",
        {
            "orders": page_obj,
            "page_obj": page_obj,
        }
    )


@login_required(login_url="login")
def order_detail(request, order_uuid):

    order = get_object_or_404(
        Order.objects
        .select_related("user")
        .prefetch_related(
            "items__product__images",
            "status_history"
        ),
        order_id=order_uuid,
        user=request.user
    )

    can_cancel = (
        order.order_status == "pending"
        and order.items.filter(status="active").exists()
    )

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "can_cancel": can_cancel,
        }
    )


@login_required(login_url="login")
@require_POST
def cancel_order(request, order_uuid):

    order = get_object_or_404(
        Order,
        order_id=order_uuid,
        user=request.user
    )

    reason = request.POST.get(
        "cancellation_reason", ""
    ).strip()

    try:
        cancel_order_items(
            order_id=order.pk,
            reason=reason
        )

        messages.success(
            request,
            "Your order has been cancelled successfully."
        )

    except OrderCancellationError as error:
        messages.error(request, str(error))

    return redirect(
        "orders:order_detail",
        order_uuid=order_uuid
    )


@login_required(login_url="login")
@require_POST
def cancel_order_item(request, order_uuid, item_id):

    order = get_object_or_404(
        Order,
        order_id=order_uuid,
        user=request.user
    )

    reason = request.POST.get(
        "cancellation_reason", ""
    ).strip()

    try:
        cancel_order_items(
            order_id=order.pk,
            item_id=item_id,
            reason=reason
        )

        messages.success(
            request,
            "Product cancelled successfully."
        )

    except OrderCancellationError as error:
        messages.error(request, str(error))

    return redirect(
        "orders:order_detail",
        order_uuid=order_uuid
    )

