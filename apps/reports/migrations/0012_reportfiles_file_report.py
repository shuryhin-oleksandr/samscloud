# Generated by Django 2.2.3 on 2019-11-26 06:53

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0011_remove_report_files'),
    ]

    operations = [
        migrations.AddField(
            model_name='reportfiles',
            name='file_report',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='reports.Report'),
        ),
    ]
