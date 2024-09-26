from datetime import date, datetime, timedelta
from urllib.parse import urljoin
import json

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import models
from django.utils.crypto import get_random_string
from django.utils.html import format_html
from django.utils.text import Truncator
from sentry_sdk import capture_exception
import requests

from ..webutils.models import _BasicAuditedModel
from ..webutils.utils import normalize_text
from .constants import SITE_CHOICES
from .utils import timestamp_to_datetime
from apps.paywall.arc_clients import IdentityClient


class ArcUserManager(models.Manager):

    def get_by_uuid(self, uuid, data=None):
        """
        Creates and saves a User with the given email, date of
        birth and password.
        """
        if not uuid:
            raise ValueError('Users must have an UUID')

        try:
            user = self.get_queryset().get(uuid=uuid)

        except ObjectDoesNotExist:
            data = self.get_profile(uuid=uuid, data=data)
            user = self.model(
                data=data,
                email=data['email'],
                uuid=uuid,
            )
            user.save(using=self._db)

        else:
            if data or not user.data:
                user.data = self.get_profile(uuid=uuid, data=data)
                user.email = user.data['email']
                user.save(using=self._db)

        return user

    def get_profile(self, uuid, data=None):
        return data if data else IdentityClient().get_profile(uuid)


class ArcUser(_BasicAuditedModel):
    uuid = models.UUIDField(
        blank=True,
        null=True,
        unique=True
    )
    email = models.EmailField(
        null=True,
        blank=True
    )
    data = JSONField(
        null=True,
        blank=True,
        verbose_name='ARC data',
        default=dict
    )
    arc_state = models.NullBooleanField(
        null=True,
        blank=True
    )
    created_on = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Fecha de registro',
        db_index=True
    )

    objects = ArcUserManager()

    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = '[ARC] Usuarios'

    def __str__(self):
        return self.get_full_name() or self.get_email()

    def get_full_name(self):
        if self.data:
            full_name = "{} {} {}".format(
                self.data.get('firstName') or '',
                self.data.get('lastName') or '',
                self.data.get('secondLastName') or '',
            ).strip()
            full_name = full_name.replace('undefined', '')
            full_name = normalize_text(full_name, 'title')
            return Truncator(full_name).chars(50)

        else:
            return '--'

    def get_email(self):
        return self.data.get('email') if self.data else '--'

    def get_attribute(self, name, mode=None):
        if self.profile and self.profile.get('attributes'):

            for atribute in self.profile['attributes']:
                if atribute['name'] == name:
                    value = atribute['value']
                    if mode and hasattr(value, mode):
                        return getattr(atribute['value'], mode)()
                    else:
                        return value

    def load_first_login(self, commit=True):
        """
            Registra el primer login
        """
        if (
            not self.first_login or
            not self.first_login_identities or
            not self.first_login_method or
            not self.first_login_device or
            not self.first_login_action
        ):
            identities = self.identities or self.first_login_identities
            if identities:
                for identity in identities:
                    if identity and identity.get('lastLoginDate'):
                        timestamp = identity.get('lastLoginDate')
                        if not self.first_login:
                            self.first_login = timestamp_to_datetime(timestamp)

                        if not self.first_login_method:
                            self.first_login_method = identity.get('type')

                        if not self.first_login_identities:
                            self.first_login_identities = identities
                        break

                if not self.first_login_identities:
                    self.first_login = None

            if not self.first_login_device:
                self.first_login_device = self.get_origin_device('title')

            if not self.first_login_action:
                self.first_login_action = self.get_origin_action_display()

            if commit:
                self.save()

    def update_arc_profile(self, commit=True):
        """
            Descarga el perfil de ARC
        """
        data = IdentityClient().get_profile(self.uuid)
        if data:
            self.profile = data
            self.identities = data.get('identities')

        if commit:
            self.save()

    def get_display_html(self):
        user_link = '/admin/arcsubs/arcuser/{}/change/'.format(self.id)
        full_name = self.get_full_name()

        return format_html(
            '<i class="fas fa-user fa-sm"></i> {full_name} '
            '<a href="{user_link}" target="_blank"><small>(ver)</small></a></br>'
            '<i class="fas fa-fingerprint"></i> {uuid}</br>'
            '<i class="fas fa-at"></i> {email}</br>',
            full_name=full_name if full_name else '--',
            user_link=user_link,
            email=self.get_email(),
            uuid=self.uuid,
        )


class Report(models.Model):
    REPORT_TYPE_EVENTS = 'subscription-event'
    REPORT_TYPE_FINANCIAL = 'financial-report'
    REPORT_TYPE_FUTURE = 'future-failed-payment'
    REPORT_TYPE_REFUND = 'refund-audit'
    REPORT_TYPE_SUMMARY = 'subscription-summary'

    REPORT_TYPE_CHOICES = (
        (REPORT_TYPE_FINANCIAL, 'Transacciones'),
        (REPORT_TYPE_EVENTS, 'Eventos'),
        (REPORT_TYPE_REFUND, 'Reembolsos'),
        (REPORT_TYPE_FUTURE, 'Próximos pagos'),
        (REPORT_TYPE_SUMMARY, 'Resumen de suscripciones'),
    )

    start_date = models.DateTimeField(
        'Fecha de inicio',
        null=True
    )
    end_date = models.DateTimeField(
        'Fecha de fin',
        null=True,
        blank=True
    )
    report_type = models.CharField(
        'Tipo',
        max_length=50,
        null=True,
        choices=REPORT_TYPE_CHOICES,
        default=REPORT_TYPE_FINANCIAL
    )
    site = models.CharField(
        'Portal',
        max_length=20,
        null=True,
        choices=SITE_CHOICES
    )
    payload = JSONField(
        'Request',
        null=True,
        blank=True
    )
    result = JSONField(
        'Responce',
        null=True,
        blank=True
    )
    error = JSONField(
        'Error',
        null=True,
        blank=True
    )
    data = models.FileField(
        'Reporte',
        null=True,
        blank=True
    )
    records = models.IntegerField(
        'Número de registros',
        null=True,
        blank=True
    )
    hits = models.IntegerField(
        'Número de intentos',
        null=True,
        blank=True,
        default=0
    )
    data_loaded = models.NullBooleanField(
        'Datos cargados',
        null=True,
        blank=True
    )

    class Meta:
        verbose_name = 'Reporte'
        verbose_name_plural = '[ARC] Reportes'

    def save(self, *args, **kwargs):

        if not self.end_date:
            self.end_date = datetime.combine(
                self.start_date.date(),
                datetime.max.time()
            ) + timedelta(seconds=1)

        self.request_report()
        self.download_report()
        super().save(*args, **kwargs)

        if self.data and self.records and self.data_loaded is None:
            self.load_data()
            super().save(*args, **kwargs)

    def datetime_to_javadate(self, _date):
        data = _date.utctimetuple()
        return "{}-{}-{}T{}:{}:{}.000Z".format(*data)

    def get_file_name(self):
        return 'reports/{day}/{jobid}_{hash}.json'.format(
            day=date.today(),
            jobid=self.result.get('jobID'),
            hash=get_random_string(length=12),
        )

    def download_report(self):
        jobid = self.result.get('jobID')

        if not jobid or self.records is not None or self.hits > 20:
            return

        url = urljoin(
            settings.PAYWALL_ARC_URL,
            "sales/api/v1/report/{jobid}/download".format(jobid=jobid)
        )

        headers = {
            'Content-Type': "application/json",
            'Authorization': "Bearer " + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': self.site
        }

        try:
            response = requests.request("GET", url, data="", headers=headers)
            result = response.json()

        except Exception:
            capture_exception()

        else:
            if response.status_code == 200:
                content = ContentFile(response.content)
                file_path = default_storage.save(self.get_file_name(), content)

                self.error = None
                self.data = file_path
                self.records = len(result)
            else:
                self.error = result
                self.hits += 1

    def request_report(self):

        if self.result and self.result.get('jobID'):
            return

        headers = {
            'content-type': 'application/json',
            'Authorization': 'Bearer ' + settings.PAYWALL_ARC_TOKEN,
            'Arc-Site': self.site
        }
        self.payload = {
            "name": "report",
            "startDate": self.datetime_to_javadate(self.start_date),
            "endDate": self.datetime_to_javadate(self.end_date),
            "reportType": self.report_type,
            "reportFormat": "json"
        }
        url = urljoin(settings.PAYWALL_ARC_URL, 'sales/api/v1/report/schedule')
        try:
            response = requests.post(url, json=self.payload, headers=headers)
            result = response.json()

        except Exception:
            capture_exception()

        else:
            self.result = result

    def load_data(self):
        from ..paywall.models import Subscription, FinancialTransaction

        if not self.data or not self.records or self.data_loaded is not None:
            return

        if self.report_type == self.REPORT_TYPE_FINANCIAL:
            try:
                records = json.loads(self.data.read())

                for record in records:
                    subscription, created = Subscription.objects.get_or_create_subs(
                        site=self.site,
                        subscription_id=record['subscriptionId'],
                        sync_data=False,
                    )
                    subscription.get_or_create_payment(record['orderNumber'])

                    FinancialTransaction.objects.get_or_create_by_report(
                        site=self.site,
                        report=record,
                    )

            except Exception:
                capture_exception()
                self.data_loaded = False

            else:
                self.data_loaded = True

        elif self.report_type == self.REPORT_TYPE_SUMMARY:
            self.data_loaded = True


class Event(models.Model):
    index = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='Code',
    )
    event_type = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Tipo',
    )
    message = JSONField(
        null=True,
        blank=True,
        verbose_name='Message',
    )
    site = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        verbose_name='Site',
    )
    timestamp = models.BigIntegerField(
        null=True,
        blank=True,
        verbose_name='timestamp',
    )

    class Meta:
        verbose_name = 'Notificación'
        verbose_name_plural = '[ARC] Notificaciones'
