# Generated by Django 4.1.1 on 2022-09-27 08:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('iam', '0002_alter_user_managers_alter_group_gid'),
    ]

    operations = [
        migrations.AlterField(
            model_name='group',
            name='display_name',
            field=models.CharField(help_text='This name will be used to display on the screen.', max_length=128, verbose_name='display name'),
        ),
    ]