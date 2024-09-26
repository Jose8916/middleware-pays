from apps.siebel.models import LogRenovationPiano
from apps.piano.models import RenovationPiano, PromotionTerm, PromotionPiano
from django.utils import timezone
from datetime import datetime
from django.conf import settings
import requests
from sentry_sdk import capture_exception
from apps.piano.utils.utils_functions import get_start_subscription


class SiebelConciliationSender(object):
    def __init__(self, operation, test_mode):
        self.operation = operation
        self.subscription = operation.subscription
        self.profile = operation.subscription.payment_profile
        self.siebel_renovation = \
            self.operation.siebel_renovation if self.operation.siebel_renovation else RenovationPiano()
        self.log_siebel_renovation = LogRenovationPiano(transaction=self.operation)
        self.test_mode = test_mode

    def format_local_date(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, '%m/%d/%Y')
            tz = timezone.get_current_timezone()
            date_payment_local_time = date_obj.astimezone(tz)
            return date_payment_local_time.strftime("%d/%m/%Y")
        except:
            return ''

    def get_renovation_promotion(self, operation):
        if operation.subscription.start_date >= get_start_subscription(operation.subscription.app_id):
            if operation.initial_payment:
                payment_billing_plan_table = operation.term.get('payment_billing_plan_table')
                for payment_table in payment_billing_plan_table:
                    if payment_table.get('isTrial') == 'true':
                        return True
        return False

    def renovar_suscripcion(self, cod_delivery, renovacion, type_conciliation, num_liquidacion, period_from, period_to):
        """
        renovacion = 1, quiere decir que la suscripcion se debe renovar y mantener la promocion
        renovacion = 0, quiere decir que la suscripcion se debe renovar pero ya no tendra promocion
        """
        type_error = None
        try:
            if period_from and period_to:
                dict_request = {
                    'cod_delivery': cod_delivery,
                    'renovacion': renovacion,
                    'fchIniRenovacion': period_from,
                    'num_liquidacion': num_liquidacion,
                    'fchFinRenovacion': period_to
                }
                self.log_siebel_renovation.siebel_request = dict_request
                url_renovacion = '{domain}/wsSuscripcionesPaywall/renovar.suscripcion?codDelivery={delivery}' \
                                 '&valRenovacion={renovacion}&fchIniRenovacion={period_from}' \
                                 '&fchFinRenovacion={period_to}&num_liquida_id={num_liquidacion}'.format(
                                    domain=settings.PAYWALL_SIEBEL_IP,
                                    delivery=cod_delivery,
                                    renovacion=renovacion,
                                    period_from=period_from,
                                    period_to=period_to,
                                    num_liquidacion=num_liquidacion
                                    )
                PARAMS = {}
                if self.test_mode:
                    print(url_renovacion)
                else:
                    try:
                        response = requests.get(url=url_renovacion, params=PARAMS)
                        data = response.json()
                    except Exception as e:
                        print(e)
                        capture_exception()
                    else:
                        if response.status_code == 200:
                            if str(data.get('response').get('respuesta', '')) == '1':
                                self.siebel_renovation.state = True
                                self.log_siebel_renovation.state = True
                            else:
                                self.siebel_renovation.state = False
                                self.log_siebel_renovation.state = False
                                type_error = {num_liquidacion: data}

                            if not self.siebel_renovation.siebel_hits:
                                self.siebel_renovation.siebel_hits = 1
                            else:
                                self.siebel_renovation.siebel_hits += 1

                            self.siebel_renovation.payu_transaction_id = num_liquidacion
                            self.siebel_renovation.siebel_request = dict_request
                            self.siebel_renovation.siebel_response = data
                            self.siebel_renovation.save()

                            self.operation.siebel_renovation = self.siebel_renovation
                            self.operation.save()

                        self.log_siebel_renovation.siebel_response = data
                        self.log_siebel_renovation.save()
                    return type_error

        except Exception as e:
            print('error en renovar suscripcion ' + str(e))
            capture_exception()
            return ''

    def renovation_send(self, access_from, access_to):
        type_conciliation = 'recurrence'
        promotion_revenue = None

        id_delivery = self.subscription.delivery
        ente_code = self.profile.siebel_entecode
        num_liquidacion = self.operation.payu_transaction_id
        if access_from and access_to:
            period_from = self.format_local_date(access_from)
            period_to = self.format_local_date(access_to)
        else:
            period_from = self.format_local_date(self.operation.access_from)
            period_to = self.format_local_date(self.operation.access_to)
        """
            renovar = 1, quiere decir que la suscripcion se debe renovar y mantiene la promocion
            renovar = 0, quiere decir que la suscripcion se debe renovar pero ya no tendra promocion
        """
        if ente_code and id_delivery and num_liquidacion:
            is_trial = self.get_renovation_promotion(self.operation)
            if PromotionPiano.objects.filter(subscription=self.operation.subscription).exists():
                promotion_piano = PromotionPiano.objects.get(subscription=self.operation.subscription)
                promotion = PromotionTerm.objects.filter(
                    term=self.operation.term,
                    promotion_id=promotion_piano.promotion_id
                )
                promotion_revenue = promotion.indefinite_promotion
                if promotion_revenue:
                    print('ingresa a promocion indefinida' + str(self.operation.subscription))

            if self.operation.term.indefinite_promotion or is_trial or promotion_revenue:
                renovar = 1
            else:
                renovar = 0

            if self.operation.initial_payment is not None:
                return self.renovar_suscripcion(
                    id_delivery,
                    renovar,
                    type_conciliation,
                    num_liquidacion,
                    period_from,
                    period_to
                )
        else:
            print('Delivery o entecode No encontrado')