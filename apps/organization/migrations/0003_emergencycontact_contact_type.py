# Generated by Django 2.2.3 on 2019-09-16 07:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0002_organizationgeofence_zone_count'),
    ]

    operations = [
        migrations.AddField(
            model_name='emergencycontact',
            name='contact_type',
            field=models.CharField(blank=True, choices=[('Emergency', 'Emergency'), ('Family', 'Family')], max_length=20, null=True),
        ),
    ]
