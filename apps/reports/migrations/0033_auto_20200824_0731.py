# Generated by Django 2.2.3 on 2020-08-24 07:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0032_auto_20200730_1015'),
    ]

    operations = [
        migrations.AlterField(
            model_name='notificationsettings',
            name='auto_route_contacts',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name='notificationsettings',
            name='auto_route_incident_organization',
            field=models.BooleanField(blank=True, default=False, null=True),
        ),
    ]
