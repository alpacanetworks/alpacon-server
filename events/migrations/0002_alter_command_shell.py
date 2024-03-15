# Generated by Django 4.1.1 on 2022-10-04 06:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='command',
            name='shell',
            field=models.CharField(choices=[('system', 'System'), ('osquery', 'Osquery'), ('internal', 'Internal')], default='system', max_length=8, verbose_name='shell'),
        ),
    ]
