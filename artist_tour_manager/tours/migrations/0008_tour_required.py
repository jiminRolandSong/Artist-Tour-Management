from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0007_assign_default_tours'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tourdate',
            name='tour',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dates', to='tours.tour'),
        ),
    ]
