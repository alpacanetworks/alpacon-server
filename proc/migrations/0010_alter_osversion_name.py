# Generated by Django 4.1.1 on 2022-10-30 14:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proc', '0009_alter_systeminfo_cpu_brand_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='osversion',
            name='name',
            field=models.CharField(max_length=32, verbose_name='name'),
        ),
    ]