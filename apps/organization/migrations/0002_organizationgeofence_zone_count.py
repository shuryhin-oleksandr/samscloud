# Generated by Django 2.2.3 on 2019-09-03 05:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='organizationgeofence',
            name='zone_count',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
