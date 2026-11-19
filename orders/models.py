
import uuid

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator


class Order(models.Model):

    ORDER_STATUS = [
        ("pending", "Pending"),
        ("shipped", "Shipped"),
        ("out_for_delivery", "Out for Delivery"),
        ("delivered", "Delivered"),
        ("cancelled", "Cancelled"),
    ]

    PAYMENT_METHODS = [
        ("cod", "Cash on Delivery"),
        ("razorpay", "Razorpay"),
        ("wallet", "Wallet"),
    ]

    PAYMENT_STATUS = [
        ("pending", "Pending"),
        ("paid", "Paid"),
        ("failed", "Failed"),
    ]

    order_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    address = models.ForeignKey(
        "my_accounts.Address",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    # Delivery address snapshot
    full_name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    house_name = models.CharField(max_length=255)
    locality = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    shipping_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    coupon_code = models.CharField(
        max_length=50,
        blank=True
    )

    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default="cod"
    )

    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS,
        default="pending"
    )

    order_status = models.CharField(
        max_length=20,
        choices=ORDER_STATUS,
        default="pending"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order {self.order_id}"


class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        "admin_panel.Product",
        on_delete=models.PROTECT
    )

    variant = models.ForeignKey(
        "admin_panel.ProductVariant",
        on_delete=models.PROTECT
    )

    product_name = models.CharField(max_length=255)

    size = models.CharField(max_length=10)

    quantity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    item_total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    ITEM_STATUS = [
        ("active", "Active"),
        ("cancelled", "Cancelled"),
        ("return_requested", "Return Requested"),
        ("returned", "Returned"),
        ]
    
    status = models.CharField(
            max_length=20,
            choices=ITEM_STATUS,
            default="active"
        )
    
    cancellation_reason = models.TextField(
            blank=True
        )
    
    cancelled_at = models.DateTimeField(
            null=True,
            blank=True
        )

    def __str__(self):
        return f"{self.product_name} - UK {self.size}"
  

class OrderStatusHistory(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="status_history"
    )

    status = models.CharField(
        max_length=20,
        choices=Order.ORDER_STATUS
    )

    changed_at = models.DateTimeField(
        auto_now_add=True
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

class ReturnRequest(models.Model):

    RETURN_STATUS = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    order_item = models.OneToOneField(
        OrderItem,
        on_delete=models.PROTECT,
        related_name="return_request"
    )

    reason = models.TextField()

    status = models.CharField(
        max_length=20,
        choices=RETURN_STATUS,
        default="pending"
    )

    requested_at = models.DateTimeField(
        auto_now_add=True
    )

    reviewed_at = models.DateTimeField(
        null=True,
        blank=True
    )
    class Meta:
        ordering = ["-requested_at"]

    def __str__(self):
        return f"Return Request - {self.order_item.product_name}"
