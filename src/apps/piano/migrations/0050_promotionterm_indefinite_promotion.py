# Generated by Django 2.2.9 on 2023-01-25 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('piano', '0049_auto_20230125_1220'),
    ]

    operations = [
        migrations.AddField(
            model_name='promotionterm',
            name='indefinite_promotion',
            field=models.NullBooleanField(verbose_name='Promocion Indefinida'),
        ),
    ]
