# Generated by Django 4.1.1 on 2022-10-18 01:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proc', '0007_auto_20221014_1852'),
    ]

    operations = [
        migrations.AddField(
            model_name='interface',
            name='link_speed',
            field=models.PositiveIntegerField(default=0, verbose_name='flags'),
        ),
        migrations.AddField(
            model_name='interface',
            name='mtu',
            field=models.PositiveIntegerField(default=1500, verbose_name='MTU'),
        ),
    ]
