# Generated by Django 4.1.1 on 2022-10-25 09:35

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('websh', '0004_alter_session_server'),
    ]

    operations = [
        migrations.AddField(
            model_name='session',
            name='root',
            field=models.BooleanField(blank=True, default=False, verbose_name='root shell'),
        ),
    ]
