# Generated by Django 2.2.3 on 2020-07-13 05:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_user_battery_power'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='is_subscribed',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='user',
            name='subscription_count',
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
    ]
