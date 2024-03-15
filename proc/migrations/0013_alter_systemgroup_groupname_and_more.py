# Generated by Django 4.2.3 on 2023-07-13 12:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('proc', '0012_delete_loadaverage'),
    ]

    operations = [
        migrations.AlterField(
            model_name='systemgroup',
            name='groupname',
            field=models.CharField(max_length=128, verbose_name='groupname'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='computer_name',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='computer name'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='cpu_type',
            field=models.CharField(blank=True, default='', max_length=32, verbose_name='CPU type'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='hardware_model',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='hardware model'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='hardware_serial',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='hardware serial'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='hardware_vendor',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='hardware vendor'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='hardware_version',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='hardware version'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='hostname',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='hostname'),
        ),
        migrations.AlterField(
            model_name='systeminfo',
            name='local_hostname',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='local hostname'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='description',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='description'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='directory',
            field=models.CharField(blank=True, default='', max_length=128, verbose_name='directory'),
        ),
        migrations.AlterField(
            model_name='systemuser',
            name='username',
            field=models.CharField(max_length=128, verbose_name='username'),
        ),
    ]
