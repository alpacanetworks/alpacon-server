# Generated by Django 4.1.1 on 2022-10-23 03:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proc', '0008_interface_link_speed_interface_mtu'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systeminfo',
            name='cpu_brand',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='CPU brand'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='cpu_subtype',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='CPU subtype'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='cpu_type',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='CPU type'),
        ),
    ]