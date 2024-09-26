# -*- coding: utf-8 -*-
from django import forms
from datetime import datetime, timedelta
from apps.arcsubs.models import ArcUser
from ..paywall.models import Plan
from django.utils.timezone import get_default_timezone
from apps.paywall.arc_clients import search_user_arc_param
from apps.pagoefectivo.models import CIP, PaymentTrackingPE
from apps.paywall.arc_clients import IdentityClient
from sentry_sdk import capture_event
from apps.paywall.utils import utc_to_lima_time_zone
from apps.pagoefectivo.utils import get_device, get_user_agent_pretty, get_browser_version, get_os_version, \
    get_device_user_agent
from apps.pagoefectivo.constants import test
from django.utils import formats, timezone
from django.conf import settings


class CIPForm(forms.ModelForm):
    arc_user = None
    date_expiry = forms.DateTimeField(input_formats=['%Y-%m-%d %H:%M:%S-05:00', ])

    def __init__(self, *args, **kwargs):
        super(CIPForm, self).__init__(*args, **kwargs)

    def clean_price_code(self):
        price_code = self.cleaned_data['price_code']

        try:
            if Plan.objects.filter(arc_pricecode=price_code).exists():
                return price_code
            else:
                raise forms.ValidationError("Price code no existe")
        except Exception:
            raise forms.ValidationError("Price code no existe")

    def clean_user_id(self):
        user_id = self.cleaned_data['user_id']

        try:
            self.arc_user = ArcUser.objects.get_by_uuid(
                uuid=user_id,
            )
        except Exception:
            raise forms.ValidationError("El usuario no existe")

    def clean_date_expiry(self):
        date_expiry = self.cleaned_data['date_expiry']
        if date_expiry:
            date_expiry = date_expiry.astimezone(
                timezone.get_current_timezone()
            )
            today = datetime.now(get_default_timezone())

            if today < date_expiry:
                return date_expiry
            else:
                raise forms.ValidationError("Fecha invalida")
        else:
            date_expiry = datetime.now(get_default_timezone()) + timedelta(1)
            return date_expiry

    class Meta:
        model = CIP
        fields = (
            'currency',
            'amount',
            'user_email',
            'user_id',
            'user_name',
            'lastname_father',
            'lastname_mother',
            'user_document_type',
            'user_document_number',
            'user_phone',
            'service_id',
            'user_code_country',
            'price_code',
            'date_expiry',
            'token_authorization'
        )

    def save(self, *args, **kwargs):
        cd = self.cleaned_data
        plan = Plan.objects.get(arc_pricecode=cd.get('price_code', ''))

        date_expiry = self.cleaned_data['date_expiry']
        date_expiry = date_expiry.astimezone(
            timezone.get_current_timezone()
        )
        if plan.partner.partner_code == 'elcomercio':
            service_id = settings.SERVICE_ID_EC
        elif plan.partner.partner_code == 'gestion':
            service_id = settings.SERVICE_ID_GESTION

        try:
            self.instance.service_id = service_id
        except Exception:
            pass

        self.instance.plan = plan
        self.instance.date_expiry = date_expiry
        self.instance.arc_user = self.arc_user
        return super(CIPForm, self).save(*args, **kwargs)

    def update(self, response, cip):
        response_dict = response.json()
        data = response_dict.get('data', None)
        date_expiry_str = data.get('dateExpiry', None)
        date_expiry_array = date_expiry_str.split('-05:00')
        date_expiry_str = date_expiry_array[0].replace("T", " ")

        cip.response = response_dict
        cip.response_state = response_dict.get('code', None)
        cip.message = response_dict.get('message', None)

        cip.cip = data.get('cip', None)
        cip.amount = data.get('amount', None)
        cip.transaction_code_response = data.get('transactionCode', None)
        cip.response_date_expiry = utc_to_lima_time_zone(date_expiry_str)
        cip.cip_url = data.get('cipUrl', None)
        cip.state = CIP.STATE_PENDING
        cip.save()


class PaymentTrackingPEForm(forms.ModelForm):
    class Meta:
        model = PaymentTrackingPE
        fields = (
            'url_referer',
            'medium',
            'device',
            'confirm_subscription',
            'user_agent',
            'is_pwa'
        )

    def save(self, *args, **kwargs):
        cd = self.cleaned_data

        self.instance.device = get_device(cd.get('user_agent', ''))
        self.instance.user_agent_str = get_user_agent_pretty(cd.get('user_agent', ''))
        self.instance.browser_version = get_browser_version(cd.get('user_agent', ''))
        self.instance.os_version = get_os_version(cd.get('user_agent', ''))
        self.instance.device_user_agent = get_device_user_agent(cd.get('user_agent', ''))

        return super(PaymentTrackingPEForm, self).save(*args, **kwargs)

