# Generated by Django 4.0.6 on 2022-09-20 06:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proc', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='osversion',
            name='build',
            field=models.CharField(blank=True, default='', max_length=16, verbose_name='build'),
        ),
        migrations.AlterField(
            model_name='systempackage',
            name='source',
            field=models.CharField(blank=True, max_length=64, null=True, verbose_name='source'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='description',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='directory',
            field=models.CharField(blank=True, default='', max_length=64, verbose_name='directory'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='shell',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='shell'),
        ),
    ]
