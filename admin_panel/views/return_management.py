
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from admin_panel.decorators import admin_required
from orders.models import ReturnRequest
from orders.services import (
    review_return_request,
    ReturnRequestError,
)


@admin_required
def return_request_list(request):

    requests = (
        ReturnRequest.objects
        .select_related(
            "order_item",
            "order_item__order",
            "order_item__order__user"
        )
        .order_by("-requested_at")
    )

    selected_status = request.GET.get("status", "")

    valid_statuses = [
        value for value, label in ReturnRequest.RETURN_STATUS
    ]

    if selected_status in valid_statuses:
        requests = requests.filter(status=selected_status)
    else:
        selected_status = ""

    paginator = Paginator(requests, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "admin_panel/return_request_list.html",
        {
            "return_requests": page_obj,
            "page_obj": page_obj,
            "selected_status": selected_status,
            "status_choices": ReturnRequest.RETURN_STATUS,
        }
    )


@admin_required
@require_POST
def admin_review_return(request, request_id):

    return_request = get_object_or_404(
        ReturnRequest,
        pk=request_id
    )

    decision = request.POST.get("decision", "")

    try:
        review_return_request(
            return_request_id=return_request.pk,
            decision=decision
        )

        messages.success(
            request,
            f"Return request {decision} successfully."
        )

    except ReturnRequestError as error:
        messages.error(request, str(error))

    return redirect("admin_panel:return_request_list")
