# Generated by Django 2.2.3 on 2019-11-22 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0009_auto_20191122_1014'),
    ]

    operations = [
        migrations.AlterField(
            model_name='report',
            name='files',
            field=models.ManyToManyField(blank=True, null=True, to='reports.ReportFiles'),
        ),
    ]
