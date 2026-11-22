from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.shortcuts import redirect,get_object_or_404
from orders.models import Order,OrderItem,OrderStatusHistory
from orders.services import (cancel_order_items, create_return_request,OrderCancellationError,ReturnRequestError,)
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db.models import Q,Prefetch

@login_required(login_url="login")
def order_list(request):

    orders = (
        Order.objects.filter(user=request.user)
        .prefetch_related("items")
        .order_by("-created_at")
    )
    # SEARCH
    search_query = request.GET.get("q", "").strip()

    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query)
            | Q(items__product_name__icontains=search_query)
            | Q(order_status__icontains=search_query)
        ).distinct()


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
            "items__return_request",
            Prefetch(
        "status_history",
        queryset=OrderStatusHistory.objects.order_by(
            "changed_at", "pk"
        )
    ),
            "items__cancelled_by",
        ),
        order_id=order_uuid,
        user=request.user
    )

    can_cancel = (
        order.order_status == "pending"
        and order.items.filter(status="active").exists()
    )

    has_cancelled_items = order.items.filter(
        status="cancelled"
    ).exists()


    # Check whether the admin cancelled the order
    cancelled_by_admin = False

    if order.order_status == "cancelled":

        cancellation_history = (
            order.status_history
            .filter(status="cancelled")
            .select_related("changed_by")
            .order_by("-changed_at", "-pk")
            .first()
        )

        if (
            cancellation_history
            and cancellation_history.changed_by_id
            and cancellation_history.changed_by_id != order.user_id
            and cancellation_history.changed_by.is_staff
        ):
            cancelled_by_admin = True

    return render(
        request,
        "orders/order_detail.html",
        {
            "order": order,
            "can_cancel": can_cancel,
            "cancelled_by_admin": cancelled_by_admin,
            "has_cancelled_items": has_cancelled_items,
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
            reason=reason,
            cancelled_by=request.user
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
            reason=reason,
            cancelled_by=request.user
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

@login_required(login_url="login")
@require_POST
def request_return(request, order_uuid, item_id):

    item = get_object_or_404(
        OrderItem,
        pk=item_id,
        order__order_id=order_uuid,
        order__user=request.user
    )

    reason = request.POST.get("reason", "").strip()

    try:
        create_return_request(
            order_item_id=item.pk,
            user=request.user,
            reason=reason
        )

        messages.success(
            request,
            "Your return request has been submitted successfully."
        )

    except ReturnRequestError as error:
        messages.error(request, str(error))

    return redirect(
        "orders:order_detail",
        order_uuid=order_uuid
    )
