from django.db import models
from cloudinary.models import CloudinaryField
import uuid
class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
# Create your models here.
class Product(models.Model):
    uuid=models.UUIDField(default=uuid.uuid4,unique=True,editable=False)
    class ColorChoices(models.TextChoices):
        BLACK = "Black", "Black"
        WHITE = "White", "White"
        BROWN = "Brown", "Brown"
        RED = "Red", "Red"
        MULTICOLOR = "Multicolor", "Multicolor"

    class OccasionChoices(models.TextChoices):
        CASUAL = "Casual", "Casual"
        FORMAL = "Formal", "Formal"
        PARTY = "Party", "Party"
        WEDDING = "Wedding", "Wedding"
        FESTIVE = "Festive", "Festive"
        OFFICE = "Office", "Office"
        DAILY_WEAR = "Daily Wear", "Daily Wear"
        SPORTS = "Sports", "Sports"

    name = models.CharField(max_length=150)

    description = models.TextField()

    category = models.ForeignKey(
        "Category",
        on_delete=models.PROTECT,
        related_name="products"
    )

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    color = models.CharField(
        max_length=20,
        choices=ColorChoices.choices
    )

    occasion = models.CharField(
        max_length=20,
        choices=OccasionChoices.choices
    )

    sizes = models.JSONField(default=list)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)
    @property
    def total_stock(self):
     return sum(
        variant.stock
        for variant in self.variants.all()
    )
    def __str__(self):
        return self.name

class ProductImage(models.Model):

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="images"
    )

    image = CloudinaryField(
        "image",
        folder="hersteps/products"
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} image"

class ProductVariant(models.Model):

    class SizeChoices(models.TextChoices):
        UK_4 = "4", "UK 4"
        UK_5 = "5", "UK 5"
        UK_6 = "6", "UK 6"
        UK_7 = "7", "UK 7"
        UK_8 = "8", "UK 8"
        UK_9 = "9", "UK 9"

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="variants"
    )

    size = models.CharField(
        max_length=2,
        choices=SizeChoices.choices
    )

    stock = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("product", "size")
        ordering = ["size"]

    def __str__(self):
        return f"{self.product.name} - UK {self.size}"
