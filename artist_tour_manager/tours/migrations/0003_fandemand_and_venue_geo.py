from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0002_tourdate_created_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='venue',
            name='latitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='venue',
            name='longitude',
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True),
        ),
        migrations.AddField(
            model_name='venue',
            name='operating_cost',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.CreateModel(
            name='FanDemand',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('fan_count', models.PositiveIntegerField()),
                ('engagement_score', models.DecimalField(decimal_places=4, default=0.1, max_digits=5)),
                ('expected_ticket_price', models.DecimalField(blank=True, decimal_places=2, max_digits=8, null=True)),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tours.artist')),
                ('venue', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tours.venue')),
            ],
        ),
    ]
