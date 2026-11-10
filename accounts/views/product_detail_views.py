from django.db.models import Sum, Q,Value,IntegerField
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages
from admin_panel.models import Product





def product_detail(request, product_uuid):
    
    product = get_object_or_404(
        Product.objects.select_related("category"),
        uuid=product_uuid,
    )
    if not product.is_active or not product.category.is_active:
     messages.error(
            request,
            "Sorry! This product is currently unavailable."
        )
     return redirect("shop")
   
     # Calculate current stock from the size variants.
    variants = product.variants.all().order_by("size")
    total_stock = variants.aggregate(
        total=Coalesce(Sum("stock"), 0)
    )["total"]
     
    available_variants = variants.filter(stock__gt=0)
    is_sold_out = total_stock <= 0
    
    related_products = Product.objects.filter(category=product.category,is_active=True,category__is_active=True).exclude(
        pk=product.pk).annotate(calculated_total_stock=Coalesce(Sum("variants__stock"),Value(0),output_field=IntegerField())
    ).filter(calculated_total_stock__gt=0).prefetch_related("images").order_by("-created_at")[:4]
    
    product_images = product.images.all()
    
    reviews = []
    coupons = []
    context = {
        "product": product,
        "variants": variants,
        "available_variants": available_variants,
        "total_stock": total_stock,
        "is_sold_out": is_sold_out,
        "product_images": product_images,
        "related_products": related_products,
        "reviews": reviews,
        "coupons": coupons,
        "related_products":related_products,
    }
    return render(
        request,
        "accounts/product_detail.html",
        context,
    )


