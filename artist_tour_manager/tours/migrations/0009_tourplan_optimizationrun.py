from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tours', '0008_tour_required'),
    ]

    operations = [
        migrations.CreateModel(
            name='TourPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=150)),
                ('start_date', models.DateField()),
                ('end_date', models.DateField()),
                ('start_city', models.CharField(blank=True, max_length=120)),
                ('venue_ids', models.JSONField(blank=True, default=list)),
                ('region_filters', models.JSONField(blank=True, default=dict)),
                ('targets', models.JSONField(blank=True, default=dict)),
                ('constraints', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('artist', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='plans', to='tours.artist')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_plans', to='auth.user')),
            ],
            options={
                'unique_together': {('artist', 'name')},
            },
        ),
        migrations.CreateModel(
            name='OptimizationRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('result', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('plan', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='runs', to='tours.tourplan')),
            ],
        ),
    ]
