import uuid
from django.db import migrations


def generate_product_uuids(apps, schema_editor):

    Product = apps.get_model("admin_panel", "Product")

    for product in Product.objects.filter(uuid__isnull=True).iterator():
        product.uuid = uuid.uuid4()
        product.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("admin_panel", "0006_alter_product_uuid"),
    ]

    operations = [
        migrations.RunPython(
            generate_product_uuids,
            migrations.RunPython.noop
        ),
    ]