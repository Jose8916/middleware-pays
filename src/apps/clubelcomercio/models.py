"""
    Modelos para registrar la interacción con Club
"""

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.utils import timezone

from .clients import ClubClient
from apps.paywall.models import Subscription
from apps.webutils.models import _BasicAuditedModel


class DigitalSubscription(Subscription):

    class Meta:
        proxy = True
        verbose_name_plural = '[Club] Suscripciones Digitales'
        verbose_name = 'Suscripción digital'


class ClubSubscriptionManager(models.Manager):

    def deactivate_subscriptions(self, subscription):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not subscription:
            raise ValueError('ClubSubscription must have an subscription')

        club_subscriptions = self.get_queryset().filter(
            subscription=subscription
        ).exclude(
            is_active=False
        )
        for club_subscription in club_subscriptions:
            club_subscription.club_deactivate()


class ClubSubscription(_BasicAuditedModel):
    """
        Registra las suscripciones de Club
        verbose_name_plural = '[Club] Suscripciones Club'
    """
    # ('PAS', 'Pasaporte'),
    # ('RUC', 'RUC'),

    DOCUMENT_TYPE_CHOICES = (
        ('DNI', 'DNI'),
        ('CEX', 'Carné extranjeria'),
        ('CDI', 'Carné de diplomático'),
    )
    subscription = models.ForeignKey(
        Subscription,
        verbose_name='Subscription',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )
    email = models.EmailField(
        null=True,
        blank=True,
    )
    document_type = models.CharField(
        max_length=8,
        null=True,
        blank=True,
        verbose_name='Tipo de documento',
        choices=DOCUMENT_TYPE_CHOICES
    )
    document_number = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Número de documento',
    )
    club_activated = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Activado en Club",
    )
    club_deactivated = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Desactivado en Club",
    )
    club_updated = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Última actualización de Club",
    )
    club_is_new = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='Nuevo en Club',
    )
    club_credentials = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='Se crearon credenciales en Club',
    )
    club_data = JSONField(
        null=True,
        blank=True,
        verbose_name='Datos de Club',
    )
    club_operation = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Número de operación',
    )
    is_active = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='Estado activo',
        choices=(
            (True, 'Activado'),
            (False, 'Desactivado'),
            (None, 'Pendiente'),
        )
    )

    objects = ClubSubscriptionManager()

    class Meta:
        verbose_name = 'Suscripción Club'
        verbose_name_plural = '[Club] Suscripciones Club'

    def __init__(self, *args, **kwargs):
        # https://stackoverflow.com/questions/23361057/
        super().__init__(*args, **kwargs)
        self.initial_id = self.id
        self.initial_email = self.email
        self.initial_document_type = self.document_type
        self.initial_document_number = self.document_number

    def save(self, *args, **kwargs):

        if not self.email:
            self.email = self.subscription.payment_profile.portal_email
        if not self.document_number:
            self.document_number = self.subscription.payment_profile.prof_doc_num
        if not self.document_type:
            self.document_type = self.subscription.payment_profile.prof_doc_type

        # Asigna el código de operación
        if not self.club_operation:
            index = ClubSubscription.objects.filter(
                subscription=self.subscription
            ).count()
            self.club_operation = '{}{}'.format(
                self.subscription.arc_id,
                index
            )
        super().save(*args, **kwargs)

        # if self.initial_id and (
        #     self.initial_email != self.email or
        #     self.initial_document_type != self.document_type or
        #     self.initial_document_number != self.document_number
        # ):
        #     self.club_update()

    def club_activate(self):
        club_integration, _ = ClubIntegration.objects.get_or_create(
            club_subscription=self,
            action=ClubIntegration.ACTION_ACTIVATE
        )
        club_integration.apply_activate()

    def club_deactivate(self):
        club_integration, _ = ClubIntegration.objects.get_or_create(
            club_subscription=self,
            action=ClubIntegration.ACTION_DEACTIVATE
        )
        club_integration.apply_deactivate()

    def club_update(self):
        club_integration = ClubIntegration.objects.create(
            club_subscription=self,
            action=ClubIntegration.ACTION_UPDATE
        )
        club_integration.apply_update()


class ClubIntegration(_BasicAuditedModel):
    """
        Registra las acciones de Club
    """
    ACTION_ACTIVATE = 1
    ACTION_DEACTIVATE = 2
    ACTION_UPDATE = 3

    club_subscription = models.ForeignKey(
        ClubSubscription,
        verbose_name='Suscripción Club',
        on_delete=models.PROTECT,
        null=True,
        editable=False,
    )
    action = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Tipo de Envio',
        choices=(
            (ACTION_ACTIVATE, 'Alta'),
            (ACTION_DEACTIVATE, 'Baja'),
            (ACTION_UPDATE, 'Actualización'),
        ),
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

    class Meta:
        verbose_name = 'Club Acción'
        verbose_name_plural = 'Club Acciones'

    def register_hit(self, payload, result, http_status_code):
        self.hits += 1  # Incrementa el número de intentos
        self.payload = payload
        self.result = result
        # Coloca estado completado si el envío fue correcto
        self.status_ok = http_status_code == 200
        self.save()

    def apply(self):
        if self.action == self.ACTION_ACTIVATE:
            self.apply_activate()

        elif self.action == self.ACTION_DEACTIVATE:
            self.apply_deactivate()

        elif self.action == self.ACTION_UPDATE:
            self.apply_update()

    def apply_activate(self):
        club_client = ClubClient(log_class=ClubLog)
        club_client.integration_activate(club_integration=self)

    def apply_deactivate(self):
        club_client = ClubClient(log_class=ClubLog)
        club_client.integration_deactivate(club_integration=self)

    def apply_update(self):
        club_client = ClubClient(log_class=ClubLog)
        club_client.integration_update(club_integration=self)


class ClubLog(_BasicAuditedModel):
    """
        Registra las interacciones con el API de Club
    """
    club_integration = models.ForeignKey(
        ClubIntegration,
        verbose_name='Club Integracion',
        on_delete=models.CASCADE,
        null=True,
        editable=False,
    )
    url = models.URLField(
        null=True,
        blank=True,
        verbose_name='API',
    )
    request_json = JSONField(
        null=True,
        blank=True,
        verbose_name='Envío JSON',
    )
    request_text = models.TextField(
        null=True,
        blank=True,
        verbose_name='Envío',
    )
    response_json = JSONField(
        null=True,
        blank=True,
        verbose_name='Respuesta JSON',
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
        verbose_name = 'Club Log'
        verbose_name_plural = 'Club Log'


class ClubRegister(_BasicAuditedModel):
    """
        Registra las suscripciones de Club
        verbose_name_plural = '[Piano] Suscripciones Club'
    """
    subscription_str = models.CharField(
        max_length=128,
        null=True,
        blank=True,
        verbose_name='Subscription ID',
    )
    email = models.EmailField(
        null=True,
        blank=True,
    )
    send = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='Enviado',
    )
    club_request = models.TextField(
        null=True,
        blank=True
    )
    club_response = models.TextField(
        null=True,
        blank=True
    )
    request_json = JSONField(
        null=True,
        blank=True,
        verbose_name='Envío JSON',
    )
    response_json = JSONField(
        null=True,
        blank=True,
        verbose_name='Respuesta JSON',
    )
    status_response = models.SmallIntegerField(
        null=True,
        blank=True
    )
    is_new = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='is_new',
    )
    create_credentials = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='create_credentials',
    )
    valid = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        verbose_name='valid',
    )

    class Meta:
        verbose_name = 'Suscripción Club'
        verbose_name_plural = '[PIANO] Suscripciones Club'

