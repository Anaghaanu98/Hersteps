from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0002_otpverification_last_sent_at"),
    ]

    operations = [
        migrations.AddField(
            model_name="customuser",
            name="is_google_user",
            field=models.BooleanField(default=False),
        ),
    ]
