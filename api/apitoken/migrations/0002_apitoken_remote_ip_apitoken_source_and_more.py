# Generated by Django 4.1.1 on 2022-11-20 12:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('apitoken', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='apitoken',
            name='remote_ip',
            field=models.GenericIPAddressField(editable=False, null=True, verbose_name='remote IP'),
        ),
        migrations.AddField(
            model_name='apitoken',
            name='source',
            field=models.CharField(choices=[('login', 'Browser login'), ('api', 'API registration')], default='api', editable=False, max_length=8, verbose_name='source'),
        ),
        migrations.AddField(
            model_name='apitoken',
            name='user_agent',
            field=models.CharField(default='', editable=False, max_length=256, verbose_name='user agent'),
        ),
    ]
