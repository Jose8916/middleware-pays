# Generated by Django 2.2.9 on 2022-12-26 21:54

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='SiebelSubscription',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('delivery', models.IntegerField(blank=True, null=True, verbose_name='Delivery')),
                ('data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Datos')),
                ('subscriber_data', django.contrib.postgres.fields.jsonb.JSONField(blank=True, null=True, verbose_name='Datos del suscriptor')),
            ],
        ),
    ]
