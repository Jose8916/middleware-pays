from django.db import models
from datetime import datetime, timedelta
from uuid import uuid4
import json

from django.conf import settings
from django.contrib.postgres.fields import ArrayField, JSONField
from apps.pagoefectivo.constants.test import *
from apps.paywall.constants import DOC_TYPE
from apps.webutils.utils import normalize_text
from django.utils.text import Truncator
from ..webutils.models import _BasicAuditedModel
from ..arcsubs.models import ArcUser
from apps.paywall.models import Plan, Subscription, PaymentProfile
from django.utils.html import format_html, format_html_join
from django.utils import formats, timezone


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


class PaymentTrackingPE(_BasicAuditedModel):
    ACCEPT_PURCHASE = 1
    NOT_ACCEPTS_PURCHASE = 2
    NOT_GO_THROUGH_FLOW = 3

    IS_PWA = 1
    NO_PWA = 2

    url_referer = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='Url Referer',
    )
    medium = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='Medio',
    )
    device = models.CharField(
        max_length=40,
        null=True,
        blank=True,
        verbose_name='Dispositivo',
        help_text='',
        choices=(
            ("1", 'mobile'),
            ("2", 'desktop'),
            ("3", 'tablet'),
            ("4", 'otros')
        ),
    )
    confirm_subscription = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Confirmacion de suscripcion',
        help_text='',
        choices=(
            (ACCEPT_PURCHASE, 'Acepta doble compra'),
            (NOT_ACCEPTS_PURCHASE, 'No acepta doble compra'),
            (NOT_GO_THROUGH_FLOW, 'No paso por el flujo')
        ),
    )
    user_agent = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='User Agent',
    )
    user_agent_str = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='Browser',
    )
    browser_version = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Browser - version',
    )
    os_version = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='Sistema Operativo',
    )
    device_user_agent = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='family - brand - model',
    )
    is_pwa = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='PWA',
        help_text='',
        choices=(
            (IS_PWA, 'SI'),
            (NO_PWA, 'NO')
        ),
    )

    class Meta:
        verbose_name = 'Seguimiento de Suscripción PE'
        verbose_name_plural = 'Seguimiento de Suscripciones PE'


class SaleOrderPE(SiebelBase):
    delivery = models.IntegerField(
        verbose_name='Delivery',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Orden de Venta'
        verbose_name_plural = 'Ordenes de Venta Siebel'

    def __str__(self):
        return 'Delivery {}'.format(self.delivery)


class PaymentPE(SiebelBase):
    state = models.BooleanField(
        default=False,
        verbose_name='state',
    )
    cod_response = models.IntegerField(
        verbose_name='cod_response',
        null=True,
        blank=True
    )
    rate_total_sent_conciliation = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        verbose_name='Total'
    )

    class Meta:
        verbose_name = 'Pago Siebel'
        verbose_name_plural = 'Pagos Siebel'

    def __str__(self):
        return 'ID {}'.format(self.id)


class CIP(_BasicAuditedModel):
    STATE_PENDING = '1'
    STATE_CANCELLED = '2'
    STATE_EXPIRED = '3'
    STATE_ANNULLED = '4'

    LINKEADO = '1'
    ERROR_EN_LINKEO = '2'
    LINKED_NO_ENVIADO = '3'

    state = models.CharField(
        verbose_name='Estado',
        null=True,
        blank=True,
        max_length=2,
        choices=(
            (STATE_PENDING, 'Pendiente de Pago'),
            (STATE_CANCELLED, 'Cancelado'),
            (STATE_EXPIRED, 'Expirado'),
            (STATE_ANNULLED, 'Anulado'),
        )
    )
    observation = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='Observación',
    )
    currency = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Currency',
        help_text='',
    )
    amount = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Amount',
    )
    date_expiry = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='dateExpiry',
    )
    payment_concept = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='paymentConcept',
    )
    additional_data = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='additionalData',
    )
    user_email = models.CharField(
        max_length=128,
        null=True,
        verbose_name='userEmail'
    )
    user_id = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='UUID',
    )
    user_name = models.CharField(
        max_length=128,
        null=True,
        verbose_name='userName'
    )
    lastname_father = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='Apellido Paterno'
    )
    lastname_mother = models.CharField(
        max_length=128,
        blank=True,
        null=True,
        verbose_name='Apellido Materno'
    )
    user_ubigeo = models.CharField(
        max_length=80,
        null=True,
        blank=True,
        verbose_name='userUbigeo'
    )
    user_country = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='userCountry'
    )
    user_document_type = models.CharField(
        max_length=10,
        null=True,
        verbose_name='userDocumentType',
        choices=DOC_TYPE
    )
    user_document_number = models.CharField(
        max_length=80,
        null=True,
        verbose_name='userDocumentNumber'
    )
    user_code_country = models.CharField(
        max_length=16,
        null=True,
        verbose_name='userCodeCountry'
    )
    user_phone = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='userPhone',
    )
    service_id = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='serviceId',
    )
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='user_cip',
        verbose_name='Cliente',
        on_delete=models.PROTECT,
    )
    price_code = models.CharField(
        max_length=16,
        null=True,
        blank=True,
        verbose_name='PRICE CODE',
    )
    plan = models.ForeignKey(
        Plan,
        null=True,
        related_name='plan_cip',
        verbose_name='Plan',
        on_delete=models.PROTECT
    )
    cip = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='CIP',
    )
    token_authorization = models.CharField(
        max_length=350,
        null=True,
        blank=True,
        verbose_name='Token Authorization',
    )
    request_body = JSONField(
        null=True,
        blank=True,
        verbose_name='Cuerpo de Envio'
    )
    response = JSONField(
        null=True,
        blank=True,
        verbose_name='Respuesta'
    )
    cip_url = models.CharField(
        max_length=120,
        null=True,
        blank=True,
        verbose_name='cipUrl',
    )
    transaction_code_response = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='transactionCodeResponse',
    )
    response_state = models.SmallIntegerField(
        verbose_name='Codigo de Respuesta PE',
        null=True,
        blank=True
    )
    response_date_expiry = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='dateExpiryResponse',
    )
    message = models.CharField(
        max_length=90,
        null=True,
        blank=True,
        verbose_name='Mensaje',
    )
    linked = models.CharField(
        verbose_name='Estado Linked',
        null=True,
        blank=True,
        max_length=2,
        choices=(
            (LINKEADO, 'Linkeado'),
            (ERROR_EN_LINKEO, 'Error en el Linkeo'),
            (LINKED_NO_ENVIADO, 'No enviado'),
        )
    )
    linked_request = JSONField(
        null=True,
        blank=True,
        verbose_name='Peticion Linked'
    )
    linked_response = JSONField(
        null=True,
        blank=True,
        verbose_name='Respuesta Linked'
    )
    subscription_arc_id = models.CharField(
        null=True,
        blank=True,
        max_length=20,
        verbose_name='Subscription ARC ID'
    )
    subscription = models.ForeignKey(
        Subscription,
        null=True,
        blank=True,
        verbose_name='Subscripción',
        on_delete=models.PROTECT
    )
    payment_profile = models.ForeignKey(
        PaymentProfile,
        null=True,
        blank=True,
        related_name='cip_payment_profile',
        on_delete=models.PROTECT,
        verbose_name='Perfil de pago',
    )
    siebel_sale_order = models.ForeignKey(
        SaleOrderPE,
        null=True,
        blank=True,
        related_name='siebel_sale_order_pe',
        on_delete=models.PROTECT,
        verbose_name='Siebel',
    )
    siebel_payment = models.ForeignKey(
        PaymentPE,
        null=True,
        blank=True,
        related_name='siebel_payment_pe',
        on_delete=models.PROTECT,
        verbose_name='Siebel Payment',
    )
    payment_tracking_pe = models.ForeignKey(
        PaymentTrackingPE,
        null=True,
        blank=True,
        related_name='payment_tracking_cip',
        on_delete=models.PROTECT,
        verbose_name='PaymentTrackingPE',
    )

    class Meta:
        verbose_name = 'CIP User'
        verbose_name_plural = 'CIPs Users'

    def __str__(self):
        return 'CIP {}'.format(self.cip)

    def get_full_name(self):
        if self.user_name or self.lastname_father:
            full_name = "{} {} {}".format(
                self.user_name,
                self.lastname_father,
                self.lastname_mother
            ).strip()
            full_name = normalize_text(full_name, 'title')
            return Truncator(full_name).chars(60)

        else:
            return '--'

    def get_user_display_html(self):
        full_name = self.get_full_name()

        return format_html(
            '<b>Email: </b> {user_email}</br>'
            '<b>User: </b> {full_name}</br>'
            '<b>{user_document_type}: </b> {user_document_number}</br>'
            '<b>Telefono: </b> {phone}</br>'
            '<b>Site: </b> {site}</br>'
            '<i class="fas fa-key"></i> ID {key}</br>',
            user_email=self.user_email,
            full_name=full_name,
            user_document_type=self.user_document_type or '',
            user_document_number=self.user_document_number or '',
            phone=self.user_phone or '',
            site=self.plan.partner.partner_name if self.plan else '',
            key=self.subscription.arc_id if self.subscription else '',
        )

    def get_transaction_display_html(self):
        if self.date_expiry:
            tz_date = self.date_expiry.astimezone(
                timezone.get_current_timezone()
            )
            date_expiry_format = formats.date_format(tz_date, settings.DATETIME_FORMAT)
        else:
            date_expiry_format = ''

        tz_date_created = self.created.astimezone(
            timezone.get_current_timezone()
        )

        return format_html(
            '<b>Monto: </b> {amount}</br>'
            '<b>Fecha de registro: </b> {register_date}</br>'
            '<b>Fecha de expiración: </b>{date_expiry}</br>'
            '<b>Estado: </b> {estado}</br>'
            '<b>Plan: </b> {plan}</br>',
            amount=self.amount,
            date_expiry=date_expiry_format,
            estado=self.get_state_display(),
            register_date=formats.date_format(tz_date_created, settings.DATETIME_FORMAT),
            plan=self.plan.plan_name if self.plan else ''
        )

    def get_response_display_html(self):
        if self.response_date_expiry:
            tz_date = self.response_date_expiry.astimezone(
                timezone.get_current_timezone()
            )
            date_expiry_format = formats.date_format(tz_date, settings.DATETIME_FORMAT)
        else:
            date_expiry_format = '--'

        try:
            name_link_cip = self.cip_url[:34]
        except Exception:
            name_link_cip = ''

        return format_html(
            '<b>TransactionCode: </b> {transaction_code_response}</br>'
            '<b>Fecha de expiración: </b>{date_expiry}</br>'
            '<b>cipUrl: </b><a target="blanck" href="{cip_url}">{name_link_cip}</a></br>'
            '<b>CIP: </b>{cip}</br>',
            transaction_code_response=self.transaction_code_response,
            date_expiry=date_expiry_format,
            cip_url=self.cip_url,
            cip=self.cip,
            name_link_cip=name_link_cip,
        )

    def get_siebel_html(self):
        estado_pago = 'No Enviado'
        color_e = 'black'
        if self.siebel_payment:
            if self.siebel_payment.cod_response == 1:
                estado_pago = 'Enviado'
                color_e = 'blue'
        try:
            entecode = self.payment_profile.siebel_entecode
        except Exception:
            entecode = ''

        return format_html(
            '<b>Entecode: </b>{entecode}</br>'
            '<b>Delivery: </b>{delivery}</br>'
            '<b>Pago: </b><span style="color:{color_e}">{estado_pago}</span></br>',
            delivery=self.siebel_sale_order.delivery if self.siebel_sale_order else '',
            estado_pago=estado_pago,
            color_e=color_e,
            entecode=entecode
        )

class PaymentNotification(_BasicAuditedModel):
    REGULAR_STATE = '1'
    TEST_STATE = '2'

    event_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='eventType',
        help_text='',
    )
    sub_type = models.CharField(
        verbose_name='SubTipo',
        null=True,
        blank=True,
        max_length=2,
        choices=(
            (REGULAR_STATE, 'Regular'),
            (TEST_STATE, 'Pruebas'),
        )
    )
    operation_number = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='operationNumber',
    )
    cip = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='CIP',
    )
    currency = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='currency',
    )
    amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='amount',
        editable=False,
    )
    payment_date = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de Pago'
    )
    transaction_code = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='transactionCode',
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='Payment data'
    )
    arc_user = models.ForeignKey(
        ArcUser,
        null=True,
        related_name='user_payment',
        verbose_name='Cliente',
        on_delete=models.PROTECT,
    )
    cip_obj = models.ForeignKey(
        CIP,
        null=True,
        related_name='payment_notification_cip',
        verbose_name='CIP OBJ',
        on_delete=models.PROTECT,
    )

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = 'Notificaciones'

    def get_transaction_display_html(self):
        if self.payment_date:
            tz_date = self.payment_date.astimezone(
                timezone.get_current_timezone()
            )
            payment_date_format = formats.date_format(tz_date, settings.DATETIME_FORMAT)
        else:
            payment_date_format = ''

        tz_date_created = self.created.astimezone(
            timezone.get_current_timezone()
        )

        return format_html(
            '<b>eventType : </b> {event_type}</br>'
            '<b>Sub Tipo : </b> {subtype}</br>'
            '<b>operationNumber: </b> {operation_number}</br>'
            '<b>Fecha de Recepción(Reg. de Notificación): </b> {register_date}</br>'
            '<b>Fecha de Pago: </b>{date_expiry}</br>',
            event_type=self.event_type if self.event_type else '',
            operation_number=self.operation_number or '',
            date_expiry=payment_date_format,
            register_date=formats.date_format(tz_date_created, settings.DATETIME_FORMAT),
            subtype=self.get_sub_type_display() or '',
        )

    def get_data_display_html(self):
        return format_html(
            '<b>Monto: </b> {amount}</br>'
            '<b>CIP: </b>{cip}</br>'
            '<b>Currency: </b>{currency}</br>'
            '<b>Transaction code: </b>{transaction_code}</br>',
            amount=self.amount or '',
            cip=self.cip or '',
            currency=self.currency,
            transaction_code=self.transaction_code or '',
        )