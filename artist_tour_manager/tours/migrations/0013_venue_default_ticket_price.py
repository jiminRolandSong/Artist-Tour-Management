from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("tours", "0012_tourgroupvenue_tour_venues"),
    ]

    operations = [
        migrations.AddField(
            model_name="venue",
            name="default_ticket_price",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True),
        ),
    ]
