import json
import requests

from sentry_sdk import capture_exception
from django.core.management.base import BaseCommand

from ...models import Benefit, SubscriptionBenefits, LogSubscriptionBenefits
from ....arcsubs.models import MailTemplate, SendMail
from ....webutils.utils import generate_password


class Command(BaseCommand):
    help = 'Execute Command!'
    origin = 'PAYWALL'

    def handle(self, *args, **options):

        SubscriptionBenefitsAll = SubscriptionBenefits.objects.filter(state=False)
        mail_template = MailTemplate.objects.get(state=True, event_type='benefits')
        benefit = Benefit.objects.filter(state=True)

        benefit_temp = {}
        for benefit_for in benefit:
            benefit_temp.update({benefit_for.be_code: False})

        json_benefits = benefit_temp
        subsid = None
        perfil_pago = {}
        for SubscriptionBenefit in SubscriptionBenefitsAll:
            perfil_pago = SubscriptionBenefit.subscription.perfil_pago

            try:
                benefit = SubscriptionBenefit.benefit

                # Generate password default
                password = perfil_pago.ppago_password
                if not password:
                    password = generate_password()
                    perfil_pago.ppago_password = password
                    perfil_pago.save()

                if subsid != SubscriptionBenefit.subscription.id and subsid:
                    fullname = perfil_pago.ppago_nombre + ' ' + perfil_pago.ppago_apepat + ' ' + perfil_pago.ppago_apemat

                    data = {
                        'name': fullname,
                        'password': perfil_pago.ppago_password,
                        'subs_id': SubscriptionBenefit.subscription.id,
                        'benefits': json_benefits
                    }

                    SendMail.objects.create(
                        email=perfil_pago.ppago_email,
                        data=data,
                        mail_template_id=mail_template.id,
                    )

                    json_benefits = benefit_temp

                prodCode = SubscriptionBenefit.detail['product']
                prodPackage = SubscriptionBenefit.detail['package']

                if benefit.be_code == 'peruquiosco':
                    data = {
                        'nombre': perfil_pago.ppago_nombre,
                        'apepat': perfil_pago.ppago_apepat,
                        'apemat': perfil_pago.ppago_apemat,
                        'email': perfil_pago.ppago_email,
                        'password': password,
                        'doctipo': perfil_pago.ppago_tipodoc,
                        'docnum': perfil_pago.ppago_numdoc,
                        'fecnac': '1995-08-09',
                        'prodcod': prodCode,
                        'prodnombre': prodPackage,
                        'finicio': str(SubscriptionBenefit.date_register),
                        'fcaducidad': str(SubscriptionBenefit.date_register),
                        'migrate': 0,
                        'operacionold': '',
                        'psuscripcionid': SubscriptionBenefit.subscription.id,
                        'origen': self.origin
                    }

                    # service = benefit.
                    url = str(benefit.be_config['url']) + 'registro'
                    header = benefit.be_config['header']

                    response = requests.post(url, headers=header, data=data)

                    logReponse = {}
                    if response.status_code == 200:
                        response = response.json()

                        if int(response['status']) == 1:
                            SubscriptionBenefit.state = True
                            SubscriptionBenefit.migrate = 'OK'

                            if response['usuario'] == 'nuevo':
                                json_benefits.update({benefit.be_code: True})

                        elif int(response['status']) > 1:
                            SubscriptionBenefit.state = True
                            SubscriptionBenefit.migrate = 'ERROR'

                        logReponse = response
                    else:
                        logReponse = {"status": False, "message": "Error al enviar el servicio"}

                    LogSubscriptionBenefits.objects.create(
                        log_benefit=benefit.be_code,
                        log_type='REGISTER',
                        log_request=json.dumps(data),
                        log_response=json.dumps(logReponse),
                        subsbenefit_id=SubscriptionBenefit.id
                    )

                    SubscriptionBenefit.save()

                elif benefit.be_code == 'club':
                    url = str(benefit.be_config['url']) + 'register'
                    header = benefit.be_config['header']

                    prodCodeSiebel = SubscriptionBenefit.detail['code']
                    data = {
                        'key': header['KEY'],
                        'name': perfil_pago.ppago_nombre,
                        'mother_sure_name': perfil_pago.ppago_apemat,
                        'last_name': perfil_pago.ppago_apepat,
                        'document_type': perfil_pago.ppago_tipodoc,
                        'document_number': perfil_pago.ppago_numdoc,
                        'email': perfil_pago.ppago_email,
                        'password': password,
                        'product_code': prodCodeSiebel,
                        'package_code': prodPackage,
                        'date_initial': str(SubscriptionBenefit.date_register),
                        'date_end': str(SubscriptionBenefit.date_register),
                        'birthdate': '1995-08-09',
                        'ope_id': SubscriptionBenefit.subscription.id,
                        'state_recurrent': 1,
                        'renovacion': 0,
                        'program': prodCode,
                        'origin': self.origin
                    }

                    response = requests.post(url, headers={}, data=data)

                    logReponse = {}
                    if response.status_code == 200:
                        response = response.json()

                        if int(response['status']) == 200:
                            SubscriptionBenefit.state = True
                            SubscriptionBenefit.migrate = 'OK'

                            if response['is_new']:
                                json_benefits.update({benefit.be_code: True})

                        logReponse = response
                    else:
                        logReponse = {"status": False, "message": "Error al enviar el servicio"}

                    LogSubscriptionBenefits.objects.create(
                        log_benefit=benefit.be_code,
                        log_type='REGISTER',
                        log_request=json.dumps(data),
                        log_response=json.dumps(logReponse),
                        subsbenefit_id=SubscriptionBenefit.id
                    )

                    SubscriptionBenefit.save()

            except Exception:
                capture_exception()

            subsid = SubscriptionBenefit.subscription.id

        if subsid:
            fullname = perfil_pago.ppago_nombre + ' ' + perfil_pago.ppago_apepat + ' ' + perfil_pago.ppago_apemat

            data = {
                'name': fullname,
                'password': perfil_pago.ppago_password,
                'subs_id': subsid,
                'benefits': json_benefits
            }

            SendMail.objects.create(
                email=perfil_pago.ppago_email,
                data=data,
                mail_template_id=mail_template.id,
            )
        print('__FINAL__')
