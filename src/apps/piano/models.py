# Create your models here.
from uuid import uuid4

from django.contrib.postgres.fields import ArrayField, JSONField
from django.db import models
from sentry_sdk import (add_breadcrumb, capture_event, capture_exception,
                        capture_message)

from apps.paywall.models import PaymentProfile, Product

from ..webutils.models import _BasicAuditedModel


class SiebelBase(_BasicAuditedModel):
    siebel_hits = models.IntegerField(
        verbose_name='Intentos a Siebel',
        default=0
    )
    siebel_request = models.TextField(
        null=True,
        blank=True
    )
    siebel_response = models.TextField(
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class SaleOrderPiano(SiebelBase):
    delivery = models.IntegerField(
        verbose_name='Delivery',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Orden de Venta'
        verbose_name_plural = 'Ordenes de Venta Siebel'

    def __str__(self):
        return 'Id {} - Delivery {}'.format(self.id, self.delivery)


class Term(_BasicAuditedModel):
    """
        Registro de un Plan, debe tener codigo de ARC.
    """
    MONTHLY = 1
    QUARTERLY = 2
    BIANNUAL = 3
    ANNUAL = 4

    plan_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Name',
    )
    plan_description = models.CharField(
        max_length=168,
        null=True,
        blank=True,
        verbose_name='Descripcion',
    )
    term_id = models.CharField(
        max_length=64,
        null=True,
        verbose_name='Term Id',
    )
    app_id = models.CharField(
        max_length=64,
        null=True,
        verbose_name='APP ID',
    )
    period = models.PositiveSmallIntegerField(
        verbose_name='Period',
        default=0,
        null=True,
        blank=True,
        choices=(
            (MONTHLY, 'Mensual'),
            (QUARTERLY, 'Trimestral'),
            (BIANNUAL, 'Semestral'),
            (ANNUAL, 'Anual'),
        ),
    )
    net_price_first_payment = models.DecimalField(
        verbose_name='Net Price Primer pago',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    indefinite_promotion = models.NullBooleanField(
        verbose_name='Promocion Indefinida',
        null=True,
        blank=True
    )
    siebel_code_promo = models.CharField(
        max_length=105,
        null=True,
        blank=True,
        verbose_name='Codigo promocional',
    )
    ticket_reference = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='Ticket de referencia',
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='Term Data'
    )
    migrated = models.PositiveSmallIntegerField(
        verbose_name='Migrado',
        default=0,
        null=True,
        blank=True,
        choices=(
            (1, 'Si'),
            (2, 'No')
        ),
    )

    product = models.ForeignKey(
        Product,
        related_name='term_product',
        verbose_name='Producto',
        null=True,
        on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Plan'
        verbose_name_plural = '[Config] Planes'
        unique_together = ('term_id', 'app_id',)

    def __str__(self):
        return '{} - {}'.format(self.plan_name or '', self.product)


class PromotionTerm(_BasicAuditedModel):
    """
       codigos de promociones para un plan
    """
    promotion_id = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='promotion piano id',
    )
    siebel_code_promo = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='siebel_code_promo',
    )
    net_price_first_payment = models.DecimalField(
        verbose_name='Net Price Primer pago',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    indefinite_promotion = models.NullBooleanField(
        verbose_name='Promocion Indefinida',
        null=True,
        blank=True
    )
    ticket_reference = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='Ticket de referencia',
    )
    term = models.ForeignKey(
        Term,
        related_name='promotion_term',
        null=True,
        on_delete=models.CASCADE
    )


class RenovationPiano(SiebelBase):
    state = models.NullBooleanField(
        verbose_name='Cod response',
        null=True,
        blank=True
    )
    payu_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Payu TransactionId',
    )

    class Meta:
        verbose_name = 'Renovacion Siebel'
        verbose_name_plural = 'Renovaciones Siebel'

    def __str__(self):
        return 'ID {}'.format(self.id)


class PaymentPiano(SiebelBase):
    state = models.BooleanField(
        default=False,
        verbose_name='state',
    )
    cod_response = models.NullBooleanField(
        verbose_name='Cod response',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Pago Siebel'
        verbose_name_plural = 'Pagos Siebel'

    def __str__(self):
        return 'ID {}'.format(self.id)


class Subscription(_BasicAuditedModel):
    delivery = models.IntegerField(
        verbose_name='Delivery',
        null=True,
        blank=True
    )
    subscription_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID',
    )
    app_id = models.CharField(
        max_length=64,
        null=True,
        verbose_name='APP ID',
    )
    uid = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='User ID (UID)',
    )
    start_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Inicio de Suscripción'
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        verbose_name='Perfil de pago',
    )
    note = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        verbose_name='Nota',
    )
    locked = models.NullBooleanField(
        'Bloqueado',
        null=True,
        blank=True
    )
    sent_club = models.BooleanField(
        null=True,
        blank=True,
        default=False,
        verbose_name='sent_club',
    )
    term = models.ForeignKey(
        Term,
        null=True,
        blank=True,
        related_name='subscription_term',
        on_delete=models.PROTECT,
        verbose_name='Term',
    )

    class Meta:
        verbose_name = 'Suscripción'
        verbose_name_plural = 'Suscripciones'
        unique_together = ('app_id', 'subscription_id',)

    def __str__(self):
        return 'ID {} [{}]'.format(self.subscription_id, self.app_id)


class PromotionPiano(_BasicAuditedModel):
    promotion_id = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='promotion_id',
    )
    promo_code_id = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        verbose_name='promo_code_id',
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        related_name='subscription_promotion_piano',
        on_delete=models.PROTECT,
        verbose_name='Subscripcion',
    )

    class Meta:
        verbose_name = 'PromotionPiano'
        verbose_name_plural = 'Promotions Piano'
        unique_together = ('promotion_id', 'subscription',)


class Unsubscribe(SiebelBase):
    sent_to_siebel = models.NullBooleanField(
        'Enviado a Siebel',
        null=True,
        blank=True
    )


class LowSubscriptions(_BasicAuditedModel):
    subs_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID',
    )
    user_email = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        verbose_name='User email',
    )
    resource_name = models.CharField(
        max_length=160,
        null=True,
        blank=True,
        verbose_name='Resource Name',
    )
    resource_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Resource ID (RID)',
    )
    start_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Inicio de Suscripción'
    )
    status = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Estado',
    )
    low_subscription = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de baja de Suscripción'
    )
    user_access_expiration_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='User Access Expiration Date'
    )
    exclude_to_send_siebel = models.NullBooleanField(
        verbose_name='Excluido de envio a Siebel',
        null=True,
        blank=True
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        related_name='subscription_low',
        on_delete=models.PROTECT,
        verbose_name='Subscripcion',
    )
    unsubscribe = models.ForeignKey(
        Unsubscribe,
        null=True,
        blank=True,
        related_name='low_subscriptions_unsubscribe',
        on_delete=models.PROTECT,
        verbose_name='Unsubscribe',
    )


class Transaction(_BasicAuditedModel):
    external_tx_id = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='External Tx ID',
    )
    tx_type = models.CharField(
        max_length=70,
        null=True,
        blank=True,
        verbose_name='Tx Type',
    )
    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Status',
    )
    term_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Term name',
    )
    term_identifier = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Term ID',
    )
    subscription_id_str = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID',
    )
    user_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='User ID (UID)',
    )
    initial_transaction = models.NullBooleanField(
        verbose_name='Transaccion inicial',
        null=True,
        blank=True
    )
    initial_payment = models.NullBooleanField(
        verbose_name='Payment inicial',
        null=True,
        blank=True
    )
    access_from = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Accesss From',
    )
    access_to = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Access To',
    )
    payment_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Payment date'
    )
    access_from_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Access From Date'
    )
    amount = models.IntegerField(
        verbose_name='Amount',
        null=True,
    )
    payu_order_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Payu OrderId',
    )
    payu_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Payu TransactionId',
    )
    payment_source_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Payment Source Type',
    )
    reconciliation_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Reconciliation Id',
    )
    id_transaction_paymentos = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Id Transaction PaymentOS',
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        null=True,
        blank=True,
        related_name='transaction_payment_profile',
        on_delete=models.PROTECT,
        verbose_name='Perfil de pago',
    )
    term = models.ForeignKey(
        Term,
        null=True,
        blank=True,
        related_name='transaction_term',
        on_delete=models.PROTECT,
        verbose_name='Term',
    )
    siebel_sale_order = models.OneToOneField(
        SaleOrderPiano,
        null=True,
        blank=True,
        related_name='transaction_siebel_sale_order',
        on_delete=models.CASCADE,
        verbose_name='Siebel O.V',
    )
    siebel_payment = models.ForeignKey(
        PaymentPiano,
        null=True,
        blank=True,
        related_name='siebel_payment_transaction',
        on_delete=models.CASCADE,
        verbose_name='Siebel Payment',
    )
    siebel_renovation = models.ForeignKey(
        RenovationPiano,
        null=True,
        blank=True,
        related_name='siebel_renovation_transaction',
        on_delete=models.CASCADE,
        verbose_name='Siebel Renovation',
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        related_name='subscription_transaction',
        on_delete=models.PROTECT,
        verbose_name='Subscripcion',
    )
    block_sending = models.NullBooleanField(
        verbose_name='Bloquear envio',
        null=True,
        blank=True
    )
    observation = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name='Observacion',
    )
    devolution = models.NullBooleanField(
        verbose_name='Devolución',
        null=True,
        blank=True
    )
    report_data = JSONField(
        null=True,
        blank=True,
    )
    original_price = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        verbose_name='original_price',
    )

    class Meta:
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'

    def __str__(self):
        return self.external_tx_id


class SubscriptionMatchArcPiano(_BasicAuditedModel):
    subscription_id_piano = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID Piano',
    )
    subscription_id_arc = models.BigIntegerField(
        default=0,
        verbose_name='ID de ARC'
    )
    brand = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Brand',
    )


class TransactionsWithNewDate(_BasicAuditedModel):
    subscription_id_piano = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID Piano',
    )
    external_tx_id = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='External Tx ID',
    )
    access_from = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Accesss From',
    )
    access_to = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Access To',
    )
    brand = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Brand',
    )


class ReportTransactions(_BasicAuditedModel):
    transaction_id = models.TextField(
        null=True,
        blank=True
    )
    tipo = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )


class BlockedSubscriptions(_BasicAuditedModel):
    subscription_id_piano = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID Piano',
    )
    type = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Tipo',
    )


class EnableSubscriptions(_BasicAuditedModel):
    subscription_id_piano = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID Piano',
    )
    type = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Tipo',
    )


class LoadReport(_BasicAuditedModel):
    export_id_recognition = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Export Id Recognition',
    )
    export_id_transaction_report = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Export Id Transaction',
    )
    brand = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Marca',
    )


class SubscriptionToFix(_BasicAuditedModel):
    subscription_id = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID',
    )
    payu_transaction_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Payu TransactionId',
    )

