# Generated by Django 2.2.3 on 2019-11-20 11:29

from django.db import migrations, models
import django.db.models.deletion
import django.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('organization', '0008_auto_20190920_1116'),
        ('accounts', '0002_user_battery_power'),
        ('reports', '0002_auto_20191118_0907'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('timestampedmodel_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='accounts.TimeStampedModel')),
                ('maintenance_id', models.CharField(max_length=20)),
                ('details', models.TextField()),
                ('address', models.CharField(max_length=100)),
                ('latitude', models.CharField(max_length=10)),
                ('longitude', models.CharField(max_length=10)),
                ('send_anonymously', models.BooleanField(default=False)),
                ('organization', models.ForeignKey(on_delete=django.db.models.fields.CharField, to='organization.OrganizationProfile')),
                ('report_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='reports.ReportType')),
            ],
            bases=('accounts.timestampedmodel',),
        ),
    ]
