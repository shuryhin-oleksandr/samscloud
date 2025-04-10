# Generated by Django 2.2.3 on 2020-07-21 10:31

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0029_auto_20200716_1557'),
    ]

    operations = [
        migrations.AlterField(
            model_name='usergeofencestatus',
            name='emergency',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignedemergency', to='organization.EmergencyContact'),
        ),
        migrations.AlterField(
            model_name='usergeofencestatus',
            name='geofence',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignedgeofence', to='reports.UserGeofences'),
        ),
        migrations.AlterField(
            model_name='usergeofencestatus',
            name='user',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='assignedgeofenceuser', to=settings.AUTH_USER_MODEL),
        ),
    ]
