from django.db import models

from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid


class Cart(models.Model):
    uuid = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    variant = models.ForeignKey(
        "admin_panel.ProductVariant",
        on_delete=models.CASCADE,
        related_name="cart_items"
    )

    quantity = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "variant"],
                name="unique_user_cart_variant"
            )
        ]

    def __str__(self):
        return (
            f"{self.user.username} - "
            f"{self.variant.product.name} - "
            f"UK {self.variant.size} - "
            f"Qty {self.quantity}"
        )

