# Generated by Django 2.2.9 on 2022-12-29 17:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('paywall', '0211_auto_20221018_1527'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentprofile',
            name='note',
            field=models.CharField(blank=True, help_text='Nota', max_length=120, null=True, verbose_name='Nota'),
        ),
    ]
