# Generated by Django 2.2.9 on 2023-01-24 20:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('piano', '0046_promotionterm'),
    ]

    operations = [
        migrations.CreateModel(
            name='PromotionPiano',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Creado')),
                ('last_updated', models.DateTimeField(auto_now=True, null=True, verbose_name='Modificado')),
                ('promotion_id', models.CharField(blank=True, max_length=250, null=True, verbose_name='promotion_id')),
                ('promo_code_id', models.CharField(blank=True, max_length=250, null=True, verbose_name='promo_code_id')),
                ('subscription', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='subscription_promotion_piano', to='piano.Subscription', verbose_name='Subscripcion')),
            ],
            options={
                'verbose_name': 'PromotionPiano',
                'verbose_name_plural': 'Promotions Piano',
                'unique_together': {('promotion_id', 'subscription')},
            },
        ),
    ]
