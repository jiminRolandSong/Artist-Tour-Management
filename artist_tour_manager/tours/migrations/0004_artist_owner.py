from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0003_fandemand_and_venue_geo'),
    ]

    operations = [
        migrations.AddField(
            model_name='artist',
            name='owner',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='artists', to='auth.user'),
        ),
    ]
