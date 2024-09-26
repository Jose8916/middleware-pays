# from dal import autocomplete
import datetime

from django import forms
from captcha.fields import ReCaptchaField
from django.utils.translation import ugettext_lazy as _
from django.contrib.admin.widgets import AdminDateWidget
from .models import PaymentProfile, Operation, Payment
from ..arcsubs.models import ArcUser
from apps.siebel.models import SiebelConfirmationPayment
from apps.pagoefectivo.models import CIP
from sentry_sdk import capture_event


class RangeDateForm(forms.Form):
    """Form de calendarios de busqueda
    """
    start_date = forms.DateField(
        widget=AdminDateWidget,
        initial=datetime.date.today,
        label=_(u'Desde'),
        required=True,
    )
    end_date = forms.DateField(
        widget=AdminDateWidget,
        initial=datetime.date.today,
        label=_(u'Hasta'),
        required=True,
    )


class FormWithCaptcha(forms.Form):
    captcha = ReCaptchaField()


class PaymentProfileForm(forms.ModelForm):
    uuid = forms.CharField(required=False)

    def __init__(self, *args, **kwargs):
        super(PaymentProfileForm, self).__init__(*args, **kwargs)

    class Meta:
        model = PaymentProfile
        fields = (
            'prof_name',
            'prof_lastname',
            'prof_lastname_mother',
            'prof_doc_type',
            'prof_doc_num',
            'prof_phone',
            'portal_email'
        )

    def save(self, *args, **kwargs):
        cd = self.cleaned_data
        arc_user = ArcUser.objects.get_by_uuid(
            uuid=cd.get('uuid', '')
        )
        self.instance.arc_user = arc_user
        meal = super(PaymentProfileForm, self).save(*args, **kwargs)
        return meal

    def get(self):
        cd = self.cleaned_data
        # cd.pop('uuid')

        try:
            # return PaymentProfile.objects.get(**cd)
            return PaymentProfile.objects.get(
                prof_name=cd.get('prof_name', ''),
                prof_lastname=cd.get('prof_lastname', ''),
                prof_lastname_mother=cd.get('prof_lastname_mother', ''),
                prof_doc_type=cd.get('prof_doc_type', ''),
                prof_doc_num=cd.get('prof_doc_num', ''),
                prof_phone=cd.get('prof_phone', ''),
                portal_email=cd.get('portal_email', '')
            )
        except Exception:
            return None


class SiebelConfirmationPaymentForm(forms.ModelForm):
    fecha_de_emision = forms.DateTimeField(input_formats=['%Y-%m-%d', ])

    def __init__(self, *args, **kwargs):
        super(SiebelConfirmationPaymentForm, self).__init__(*args, **kwargs)

    class Meta:
        model = SiebelConfirmationPayment
        fields = (
            'nro_renovacion',
            'cod_interno_comprobante',
            'folio_sunat',
            'monto',
            'fecha_de_emision',
            'code_ente',
            'cod_delivery',
            'num_liquidacion'
        )

    def save(self, *args, **kwargs):
        cd = self.cleaned_data
        if cd.get('num_liquidacion', '') == 'VENTA':
            operation_obj = Operation.objects.filter(
                payment__subscription__delivery=cd.get('cod_delivery', ''),
                ope_amount__gte=5
            ).order_by('created').first()
            if operation_obj:
                self.instance.operation = operation_obj
            else:
                try:
                    cip_obj = CIP.objects.get(
                        siebel_sale_order__delivery=cd.get('cod_delivery', '')
                    )
                    self.instance.cip = cip_obj
                except Exception:
                    pass
        else:
            try:
                operation_ = Operation.objects.get(
                    payment__payu_transaction=cd.get('num_liquidacion', '')
                )
            except Exception:
                operation_ = None
                pass

            if operation_:
                self.instance.operation = operation_

        payment_response = super(SiebelConfirmationPaymentForm, self).save(*args, **kwargs)
        return payment_response