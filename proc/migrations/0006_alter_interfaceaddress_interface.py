# Generated by Django 4.0.6 on 2022-09-23 13:22

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('proc', '0005_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='interfaceaddress',
            name='interface',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='addresses', related_query_name='address', to='proc.interface', verbose_name='interface'),
        ),
    ]
