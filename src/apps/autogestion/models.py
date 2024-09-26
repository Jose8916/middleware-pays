from django.db import models
from django.contrib.postgres.fields import JSONField


class SiebelSubscription(models.Model):
    delivery = models.IntegerField(
        verbose_name='Delivery',
        null=True,
        blank=True
    )
    data = JSONField(
        verbose_name='Datos',
        null=True,
        blank=True,
    )
    subscriber_data = JSONField(
        verbose_name='Datos del suscriptor',
        null=True,
        blank=True,
    )
