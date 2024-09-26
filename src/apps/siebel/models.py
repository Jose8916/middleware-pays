from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from apps.paywall.models import Plan, PaymentProfile, Operation, Subscription
from apps.pagoefectivo.models import CIP
from apps.piano.models import Transaction, LowSubscriptions
from ..ubigeo.models import Ubigeo
from ..webutils.models import _BasicAuditedModel
from .clients.suspension import SuspensionClient


TIPOESTADO = (
    (1, 'Activo'),
    (0, 'Inactivo'),
)

TIPOPRECIO = (
    (1, 'Promoción'),
    (0, 'Precio Regular'),
    (2, 'Promoción Indefinida'),
)

TIPDIR_CHOICES = (
    ('via', 'Via'),
    ('poblacion', 'Poblacion'),
)


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


class SiebelSubscriptionManager(models.Manager):

    def get_or_create_siebel(self, subscription):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not subscription:
            raise ValueError('Subscription must have an subscription')

        try:
            siebel_subscription = self.get_queryset().get(
                subscription=subscription
            )

        except ObjectDoesNotExist:
            created = True

            siebel_subscription = self.model(
                subscription=subscription
            )
            siebel_subscription.save(using=self._db)

        else:
            created = False

        return siebel_subscription, created


class SiebelSubscription(_BasicAuditedModel):
    STATUS_SUSPEND = 6
    STATUS_CHOICES = (
        (2, 'Pendiente'),
        (4, 'Activo'),
        (STATUS_SUSPEND, 'Suspendido'),
        (8, 'Desactivado'),
    )
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )
    siebel_delivery = models.IntegerField(
        verbose_name='Siebel Delivery',
        null=True,
        blank=True
    )
    status = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Estado',
        choices=STATUS_CHOICES,
    )

    objects = SiebelSubscriptionManager()

    def save(self, *args, **kwargs):

        if not self.siebel_delivery:
            self.siebel_delivery = self.subscription.get_siebel_delivery()

        super().save(*args, **kwargs)

    def siebel_deactivate(self):
        siebel_action, _ = SiebelAction.objects.get_or_create(
            siebel_subscription=self,
            action=SiebelAction.ACTION_DEACTIVATE
        )
        siebel_action.apply_deactivate()

    def siebel_suspend(self):
        siebel_action, _ = SiebelAction.objects.get_or_create(
            siebel_subscription=self,
            action=SiebelAction.ACTION_SUSPEND
        )
        siebel_action.apply_suspend()


class SiebelAction(models.Model):
    ACTION_ACTIVATE = 2
    ACTION_SUSPEND = 4
    ACTION_DEACTIVATE = 6
    ACTION_UPDATE = 8

    ACTION_CHOICES = (
        (ACTION_ACTIVATE, 'Alta'),
        (ACTION_DEACTIVATE, 'Baja'),
        (ACTION_SUSPEND, 'Suspensión'),
        (ACTION_UPDATE, 'Actualización'),
    )

    siebel_subscription = models.ForeignKey(
        SiebelSubscription,
        verbose_name='Suscripción Club',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )
    action = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Tipo de Envio',
        choices=ACTION_CHOICES,
    )
    payload = JSONField(
        null=True,
        blank=True,
        verbose_name='Datos',
    )
    result = JSONField(
        null=True,
        blank=True,
        verbose_name='Respuesta',
    )
    hits = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        default=0,
        verbose_name='Numero de intentos',
    )
    status_ok = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='estado',
        choices=(
            (True, 'Completado'),
            (False, 'Fallido'),
            (None, 'Pendiente'),
        )
    )

    def apply(self):
        if self.action == self.ACTION_ACTIVATE:
            self.apply_activate()

        elif self.action == self.ACTION_DEACTIVATE:
            self.apply_deactivate()

        elif self.action == self.ACTION_UPDATE:
            self.apply_update()

        elif self.action == self.ACTION_SUSPEND:
            self.apply_suspend()

    def apply_suspend(self):
        client = SuspensionClient(log_class=SiebelLog)
        client.siebel_suspend(siebel_action=self)

    def apply_activate(self):
        pass

    def apply_deactivate(self):
        pass

    def apply_update(self):
        pass

    def register_hit(self, result, payload, http_status_code):
        self.hits += 1  # Incrementa el número de intentos
        self.payload = payload
        self.result = result
        # Coloca estado completado si el envío fue correcto
        self.status_ok = http_status_code == 200
        self.save()


class SiebelLog(models.Model):
    """
        Registra las interacciones con el API de Siebel
    """
    siebel_action = models.ForeignKey(
        SiebelAction,
        verbose_name='Siebel Action',
        on_delete=models.CASCADE,
        null=True,
        editable=False,
    )
    url = models.URLField(
        null=True,
        blank=True,
        verbose_name='API',
    )
    request_text = models.TextField(
        null=True,
        blank=True,
        verbose_name='Envío',
    )
    response_text = models.TextField(
        null=True,
        blank=True,
        verbose_name='Respuesta',
    )
    response_code = models.SmallIntegerField(
        null=True,
        blank=True
    )
    response_time = models.FloatField(
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Siebel Log'
        verbose_name_plural = 'Siebel Log'


class SiebelConfirmationPayment(_BasicAuditedModel):
    """
        Registra las notificaciones de Pago de siebel
    """

    operation = models.ForeignKey(
        Operation,
        null=True,
        blank=True,
        related_name='siebel_operation',
        verbose_name='Confirmacion de Pago',
        on_delete=models.PROTECT
    )
    cip = models.ForeignKey(
        CIP,
        null=True,
        blank=True,
        related_name='siebel_confirmation_cip',
        verbose_name='CIP',
        on_delete=models.PROTECT
    )
    nro_renovacion = models.CharField(
        verbose_name='Número de renovación',
        null=True,
        blank=True,
        max_length=10,
    )
    cod_interno_comprobante = models.IntegerField(
        verbose_name='Codigo interno de Comprobante',
        null=True,
        blank=True
    )
    folio_sunat = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Folio Sunat',
    )
    monto = models.DecimalField(
        verbose_name='Monto total del comprobante Generado',
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True
    )
    fecha_de_emision = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de impresión del comprobante'
    )
    code_ente = models.IntegerField(
        verbose_name='Codigo Ente',
        null=True,
        blank=True
    )
    cod_delivery = models.IntegerField(
        verbose_name='Codigo Delivery',
        null=True,
        blank=True
    )
    num_liquidacion = models.CharField(
        max_length=60,
        null=True,
        blank=True,
        verbose_name='Número de Liquidación',
    )
    log_response = JSONField(
        null=True,
        blank=True,
        verbose_name='Response',
    )

    class Meta:
        verbose_name = 'Confirmacion de Pago'
        verbose_name_plural = 'Confirmacion de Pagos'


class TipoUrbanizacion(models.Model):
    tipurb_nombre = models.CharField(max_length=32, verbose_name='nombre', )
    tipurb_codigo = models.CharField(max_length=8, verbose_name='codigo')
    estado = models.IntegerField(verbose_name='estado', default=1, choices=TIPOESTADO, )

    class Meta:
        verbose_name = 'Tipo urbanización'
        verbose_name_plural = 'Tipos urbanización'

    def __unicode__(self):
        return "%s" % (self.tipurb_nombre)


class Urbanizacion(models.Model):
    urb_nombre = models.CharField(max_length=256, verbose_name='nombre', )
    estado = models.IntegerField(verbose_name='estado', default=1, choices=TIPOESTADO, )
    ubigeo = models.ForeignKey(
        Ubigeo, related_name='UrbanizacionUbigeo', verbose_name='ubigeo', null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    tipurb = models.ForeignKey(
        TipoUrbanizacion, related_name='TipourbTipurb', verbose_name='tipo urbanizacion',
        null=True,
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Urbanización'
        verbose_name_plural = 'Urbanizaciones'

    def __unicode__(self):
        return "%s - %s" % (self.tipurb.tipurb_codigo, self.urb_nombre)


class UrbanizacionUbigeo(models.Model):
    estado = models.IntegerField(verbose_name='estado', default=1, choices=TIPOESTADO, )
    urb = models.ForeignKey(
        Urbanizacion, related_name='relatedUrbUbi',
        on_delete=models.PROTECT)
    ubigeo = models.ForeignKey(
        Ubigeo, related_name='relatedUbiUrb',
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Urbanización ubigeo'
        verbose_name_plural = 'Urbanización ubigeo'


class TipoVia(models.Model):
    tipvia_nombre = models.CharField(max_length=32, verbose_name='nombre', )
    tipvia_codigo = models.CharField(max_length=8, verbose_name='codigo', unique=True)
    estado = models.IntegerField(verbose_name='estado', default=1, choices=TIPOESTADO, )

    class Meta:
        verbose_name = 'Tipo vía'
        verbose_name_plural = 'Tipos vías'

    def __unicode__(self):
        return "%s" % (self.tipvia_nombre)


class Via(models.Model):
    via_nombre = models.CharField(max_length=256, verbose_name='nombre', )
    estado = models.IntegerField(verbose_name='estado', default=1, choices=TIPOESTADO, )
    # ubigeo = models.ForeignKey(Ubigeo, related_name='viaUbigeo',verbose_name='ubigeo',null=True)
    tipvia = models.ForeignKey(
        TipoVia, related_name='viaTipvia', verbose_name='tipo via', null=True,
        on_delete=models.PROTECT)

    # urbs = models.ManyToManyField(urbanizacion, through='urbanizacion_via')
    class Meta:
        verbose_name = 'Vía'
        verbose_name_plural = 'Vías'

    def __unicode__(self):
        return "%s - %s" % (self.tipvia.tipvia_codigo, self.via_nombre)


class UrbanizacionVia(models.Model):
    estado = models.IntegerField(verbose_name='estado', default=1, choices=TIPOESTADO)
    urb = models.ForeignKey(
        Urbanizacion, related_name='relatedUrbviaUrb',
        on_delete=models.PROTECT)
    via = models.ForeignKey(
        Via, related_name='relatedUrbviaVia',
        on_delete=models.PROTECT)
    ubigeo = models.ForeignKey(
        Ubigeo, related_name='relatedUbiUrbVia',
        on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Urbanización Via Ubigeo'
        verbose_name_plural = 'Urbanización Via Ubigeo'


class Logs(_BasicAuditedModel):
    state = models.BooleanField(
        default=True,
        verbose_name='State',
    )
    delivery = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Delivery'
    )
    log_type = models.CharField(
        max_length=64,
        verbose_name='Tipo'
    )
    log_request = JSONField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = JSONField(
        null=True,
        blank=True,
        verbose_name='Response',
    )

    class Meta:
        verbose_name = 'Log Siebel'
        verbose_name_plural = 'Logs Siebel'

    def __str__(self):
        return '%s' % self.id


class Rate(_BasicAuditedModel):
    """
        Registra una tarifa de Siebel
    """

    MONTH = 1
    SEMESTER = 2
    YEAR = 3
    TRIMESTER = 4

    BILLING_FREQUENCY = (
        (MONTH, 'Mensual'),
        (SEMESTER, 'Semestral'),
        (YEAR, 'Anual'),
        (TRIMESTER, 'Trimestral'),
    )

    plan = models.ForeignKey(
        Plan,
        related_name='rates',
        verbose_name='Plan',
        null=True,
        on_delete=models.CASCADE
    )
    state = models.BooleanField(
        default=True,
        verbose_name='State',
    )
    rate_name = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Name',
    )
    siebel_id = models.IntegerField(
        null=True,
        verbose_name='Siebel ID',
    )
    siebel_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Siebel Code',
    )
    # siebel_component = models.CharField(
    #     max_length=128,
    #     null=True,
    #     blank=True,
    #     verbose_name='Siebel Component',
    # )

    rate_neto = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        verbose_name='Neto'
    )
    rate_igv = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        verbose_name='IGV'
    )
    rate_total = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        verbose_name='Total'
    )
    siebel_code_promo = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Siebel Promo',
    )
    type = models.IntegerField(
        verbose_name='Tipo',
        default=0,
        choices=TIPOPRECIO,
    )
    duration = models.IntegerField(
        verbose_name='Duración',
        null=True,
        blank=True,
    )
    billing_frequency = models.IntegerField(
        verbose_name='Frecuencia de cobro',
        null=True,
        blank=True,
        choices=BILLING_FREQUENCY,
    )

    class Meta:
        verbose_name = 'Tarifa'
        ordering = ('rate_total', )

    def __str__(self):
        return '{} S/ {}'.format(self.rate_name, self.rate_total)


class LogSiebelClient(_BasicAuditedModel):
    state = models.CharField(
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )
    email = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Email',
    )
    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        null=True,
        blank=True,
        related_name='PaymentProfile',
        verbose_name='Payment Profile',
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Log_client_siebel'
        verbose_name_plural = 'Logs_client_siebel'

    def __str__(self):
        return str(self.id)


class LogSiebelOv(_BasicAuditedModel):
    state = models.CharField(
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )

    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    operation = models.ForeignKey(
        Operation,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Log_siebel_ov'
        verbose_name_plural = 'Logs_siebel_ov'

    def __str__(self):
        return str(self.id)


class LogSiebelOvPE(_BasicAuditedModel):
    state = models.CharField(
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )
    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    cip = models.ForeignKey(
        CIP,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = '[Pago Efectivo] Log_siebel_ov'
        verbose_name_plural = '[Pago Efectivo] Logs_siebel_ov'

    def __str__(self):
        return str(self.id)


class LogSiebelOvPiano(_BasicAuditedModel):
    state = models.CharField(
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )
    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = '[Piano] Log_siebel_ov'
        verbose_name_plural = '[Piano] Logs_siebel_ov'

    def __str__(self):
        return str(self.id)


class LogSiebelConciliacion(_BasicAuditedModel):
    state = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )

    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    operation = models.ForeignKey(
        Operation,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )
    log_recurrence_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request Recurrence',
    )
    log_recurrence_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response Recurrence',
    )
    type = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        verbose_name='Tipo',
        choices=(
            ('web', 'WEB'),
            ('recurrence', 'RECURRENCE'),
        )
    )

    class Meta:
        verbose_name = 'Log_siebel_conciliacion'
        verbose_name_plural = 'Logs_siebel_conciliacion'

    def __str__(self):
        return str(self.id)


class LogSiebelConciliacionPE(_BasicAuditedModel):
    state = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )

    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    cip = models.ForeignKey(
        CIP,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = '[Pago Efectivo] Log_siebel_conciliacion'
        verbose_name_plural = '[Pago Efectivo] Logs_siebel_conciliacion'

    def __str__(self):
        return str(self.id)


class LogSiebelPaymentPiano(_BasicAuditedModel):
    state = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    log_request = models.TextField(
        null=True,
        blank=True,
        verbose_name='Request',
    )
    log_response = models.TextField(
        null=True,
        blank=True,
        verbose_name='Response',
    )

    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = '[Piano] Log_pago'
        verbose_name_plural = '[Piano] Logs_pago'

    def __str__(self):
        return str(self.id)


class LogRenovationPiano(SiebelBase):
    state = models.CharField(
        null=True,
        blank=True,
        max_length=64,
        verbose_name='State',
        choices=(
            ('error', 'Error'),
            ('successful', 'Successful'),
            ('repetido', 'Conciliación'),
        )
    )
    error_code = models.CharField(
        max_length=64,
        null=True,
        blank=True,
        verbose_name='Error code'
    )
    fecha = models.DateTimeField(
        auto_now_add=True,
        null=True
    )
    transaction = models.ForeignKey(
        Transaction,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = '[Piano] LogRenovationPiano'
        verbose_name_plural = '[Piano] LogRenovationPiano'

    def __str__(self):
        return str(self.id)


class SiebelConfiguration(_BasicAuditedModel):
    customer_attempts = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Numero de intentos del cliente',
    )
    ov_attempts = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Numero de intentos la orden de venta',
    )
    conciliation_attempts = models.CharField(
        max_length=10,
        null=True,
        blank=True,
        verbose_name='Numero de intentos del pago',
    )
    state = models.BooleanField(
        default=False,
        verbose_name='Estado',
    )
    days_ago = models.IntegerField(
        blank=True,
        null=True,
        verbose_name='Dias atrás'
    )
    blocking = models.BooleanField(
        default=False,
        verbose_name='Bloqueo de envio',
    )
    queue_piano_vouchers = models.BooleanField(
        default=False,
        verbose_name='Bloqueo por cola de envio de renovaciones',
    )
    queue_piano_conciliation = models.BooleanField(
        default=False,
        verbose_name='Bloqueo por cola de envio de conciliaciones',
    )
    queue_piano_delivery = models.BooleanField(
        default=False,
        verbose_name='Bloqueo por cola de envio de deliverys',
    )

    class Meta:
        verbose_name = 'Siebel Configuración'
        verbose_name_plural = '[Config] Envio a Siebel'


class ReasonExclude(_BasicAuditedModel):
    reason = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Razón',
    )

    siebel_configuration = models.ForeignKey(
        SiebelConfiguration,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    def __str__(self):
        return self.reason

    class Meta:
        verbose_name = 'Razon a excluir al envio de Siebel'
        verbose_name_plural = '[Config] Razones a excluir al envio(Motivo de termino de suscripción)'


class SubscriptionExclude(_BasicAuditedModel):
    subscription = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Suscripción',
    )
    description = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Descripción',
    )
    siebel_configuration = models.ForeignKey(
        SiebelConfiguration,
        null=True,
        blank=True,
        on_delete=models.PROTECT
    )

    class Meta:
        verbose_name = 'Suscripcion a excluir en el envio de Siebel'
        verbose_name_plural = '[Config] Suscripciones a excluir en el envio de Siebel'


class LoadTransactionsIdSiebel(_BasicAuditedModel):
    transaction_id = models.TextField(
        null=True,
        blank=True
    )
    tipo = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )


class PendingSendSiebel(_BasicAuditedModel):
    transaction_id = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )
    cliente = models.TextField(
        null=True,
        blank=True
    )
    ov = models.TextField(
        null=True,
        blank=True
    )
    conciliation = models.TextField(
        null=True,
        blank=True
    )
    log_response = models.TextField(
        null=True,
        blank=True
    )


class LoadProfile(_BasicAuditedModel):
    id_profile = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )
    arc_id = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )


class CommandSiebel(_BasicAuditedModel):
    date = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )
    type = models.CharField(
        null=True,
        blank=True,
        max_length=100
    )


class ArcUnsubscribe(SiebelBase):
    sent_to_siebel = models.NullBooleanField(
        'Enviado a Siebel',
        null=True,
        blank=True
    )
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        related_name='siebel_arc_unsubscribe',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )


class LogArcUnsubscribe(SiebelBase):
    sent_to_siebel = models.NullBooleanField(
        'Enviado a Siebel',
        null=True,
        blank=True
    )
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        related_name='log_arc_unsubscribe_siebel',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )


class LogUnsubscribePiano(SiebelBase):
    sent_to_siebel = models.NullBooleanField(
        'Enviado a Siebel',
        null=True,
        blank=True
    )
    subscription_low = models.ForeignKey(
        LowSubscriptions,
        verbose_name='Subscription',
        related_name='log_unsubscribe_piano_siebel',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )
