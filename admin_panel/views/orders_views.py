from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.shortcuts import render
from django.db.models import Q

from orders.models import Order


@staff_member_required(login_url="admin_panel:admin_login")
def order_list(request):

    orders = Order.objects.select_related("user").order_by("-created_at")

    search_query = request.GET.get("q", "").strip()

    if search_query:
        filters = (
            Q(full_name__icontains=search_query)
            | Q(user__email__icontains=search_query)
        )

        try:
            import uuid
            order_uuid = uuid.UUID(search_query)
            filters |= Q(order_id=order_uuid)
        except (ValueError, AttributeError):
            pass

        orders = orders.filter(filters)

    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "admin_panel/order_list.html",
        {
            "orders": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
        }
    )