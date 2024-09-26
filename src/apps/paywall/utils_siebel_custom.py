from datetime import datetime
import socket
import time
from django.utils import formats, timezone
from django.conf import settings
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_exception
from suds.bindings import binding
from suds.client import Client as SudsClient
from suds.plugin import MessagePlugin
from suds.sudsobject import asdict
import requests

from .utils import current_time
from apps.arcsubs.utils import timestamp_to_datetime
from apps.paywall import soap_utils
from apps.paywall.models import FinancialTransaction, Payment, Operation
from apps.siebel.models import Rate, LogSiebelClient, LogSiebelOv, LogSiebelConciliacion


# binding.envns = ('soapenv', 'http://www.w3.org/2003/05/soap-envelope')
binding.envns = ('soapenv', 'http://schemas.xmlsoap.org/soap/envelope/')


def recursive_dict(d):
    out = {}
    for k, v in asdict(d).items():
        if hasattr(v, '__keylist__'):
            out[k] = recursive_dict(v)
        elif isinstance(v, list):
            out[k] = []
            for item in v:
                if hasattr(item, '__keylist__'):
                    out[k].append(recursive_dict(item))
                else:
                    out[k].append(item)
        else:
            out[k] = v
    return out


class LogPlugin(MessagePlugin):

    def __init__(self, instance, nsprefix, log_instance=None):
        self.instance = instance
        self.nsprefix = nsprefix
        self.log_instance = log_instance

    def sending(self, context):
        request = context.envelope.decode('UTF-8')

        if hasattr(self.instance, 'siebel_request'):
            self.instance.siebel_request = request
            self.instance.siebel_response = ''
            self.instance.save()

            if self.log_instance:
                self.log_instance.log_request = request
                self.log_instance.save()
        else:
            print("> SIEBEL REQUEST\n%s" % request)

    def received(self, context):
        response = context.reply

        if hasattr(self.instance, 'siebel_request'):
            if not self.instance.siebel_hits:
                self.instance.siebel_hits = 1
            else:
                self.instance.siebel_hits += 1

            self.instance.siebel_response = context.reply
            self.instance.save()

            if self.log_instance:
                self.log_instance.log_response = context.reply
                self.log_instance.save()
        else:
            print("> SIEBEL RESPONSE\n%s" % response)

    def marshalled(self, context):
        context.envelope[0].setPrefix('soapenv')
        context.envelope[1].setPrefix('soapenv')
        context.envelope[1][0].setPrefix('tem')
        context.envelope[1][0][0].setPrefix('tem')
        context.envelope[1][0][0][0].setPrefix('eco')
        context.envelope[1][0][0][0][0].setPrefix('eco')
        pref = context.envelope[1][0][0][0][0]
        for pref in context.envelope[1][0][0][0][0]:
            pref.setPrefix('eco')
            for pref2 in pref:
                pref2.setPrefix('eco')
                for pref3 in pref2:
                    pref3.setPrefix('eco')
        del context.envelope.nsprefixes['ns3']
        del context.envelope.nsprefixes['ns0']
        del context.envelope.nsprefixes['ns1']
        del context.envelope.nsprefixes['ns2']
        del context.envelope.nsprefixes['xsi']
        context.envelope.nsprefixes['eco'] = self.nsprefix
        context.envelope.nsprefixes['tem'] = 'http://tempuri.org/'


class SiebelClientSender(object):
    """docstring for SiebelClientSender"""

    def __init__(self, profile):
        self.perfil_pago = profile

    def run(self):
        self.send_client()

    def send_client(self):
        message_plugin = LogPlugin(
            instance=self.perfil_pago,
            nsprefix='http://www.siebel.com/xml/ECO%20Account%20Interface%20w%20Address',
            log_instance=LogSiebelClient(payment_profile=self.perfil_pago)
        )
        client = SudsClient(
            settings.PAYWALL_SIEBEL_URL + 'wscrearcliente.asmx?wsdl',
            plugins=[message_plugin],
            cache=None
        )

        client.options.prettyxml = True
        account = client.factory.create('ns0:CrearCliente_1_Input')

        try:
            account.ListOfEcoAccountInterfaceWAddress2.Account = [self.get_client_data()]
            result = client.service.CrearCliente(account)
            result = recursive_dict(result)

        except socket.error:
            capture_exception()

        except Exception:
            capture_exception()

        else:
            if 'EnteCliente' in result and result['EnteCliente']:
                self.perfil_pago.siebel_name = result['NameCliente']
                self.perfil_pago.siebel_entecode = result['EnteCliente']
                self.perfil_pago.siebel_entedireccion = result['EnteDireccion']
                self.perfil_pago.siebel_direction = result['Nombre_spcDireccion']
                self.perfil_pago.siebel_date = current_time()
                self.perfil_pago.save()

    def get_client_data(self):
        account = {
            "AccountStatus": 'Activo',
            "ECApellidoMaterno": self.get_apellido_materno(),
            "ECApellidoPaterno": self.get_apellido_paterno(),
            "ECFechaFunNac": self.get_fecha_nacimiento(),
            "ECNombres": self.get_ec_nombres(),
            "ECSexo": self.get_sexo(),
            "ECTipoCliente": self.get_tipo_cliente(),
            "ListOfCutAddress": [{"CutAddress": [self.get_address_data()]}],
            "Location": self.get_numero_documento(),
            "LocationType": self.get_tipo_documento(),
            "MainEmailAddress": self.get_email(),
            "Name": self.get_siebel_name(),
            "PrimaryOrganization": 'Default Organization',
            "PrimaryOrganizationId": '0-R9NH',
            "Type": 'Nacional',
        }

        return account

    def get_address_data(self):
        # # Debe validar que el plan es sólo digital
        return {
            "AccountId": "",
            "AddrDescription": "NFSDNHSN LIMA",
            "ApartmentNumber": "",
            "City": "LIMA",
            "Country": "PERU",
            "ECAddressName": "LIMABDSDDN",
            "ECAnexo": "",
            "ECCentroPoblado": "",
            "ECCodigoCentroPoblado": 0,
            "ECCodigoDepartamento": 1,
            "ECCodigoDistrito": 1,
            "ECCodigoDptoPisoInt": "CH",
            "ECCodigoPais": 1,
            "ECCodigoVia": 52406,
            "ECCoordX": -76.9770383835,
            "ECCoordY": -12.0710071,
            "ECDenominacion": "",
            "ECDptoPisoInt": "",
            "ECEtapaSector": "",
            "ECNombreLote": "",
            "ECNombreManzana": "",
            "ECNombreTipVia": "AVENIDA",
            "ECNumeroPuerta": 454,
            "ECStreetAddress": "LIMABDSDDN",
            "ECTCPNombre": "",
            "ECTipoDptoPisoIntNom": "",
            "ECTipoEtapaSectorCod": "Z",
            "ECTipoEtapaSectorNom": "",
            "ECVia": "LIMA",
            "FaxNumber": "",
            "IntegrationId": "",
            "IntegrationId2": "",
            "LandlordPhoneNumber": "",
            "PhoneNumber": 3456789,
            "PrimaryAddressFlg": "Y",
            "Province": "LIMA",
            "UTMEasting": "AV"
        }

    def get_numero_documento(self):
        numero = self.perfil_pago.prof_doc_num or ''
        tipo = self.get_tipo_documento()

        # Validar si el valor de CEX enviado es correcto porque en delivery solo aceptan 15 caracteres
        if tipo == 'CEX' and len(numero) >= 15:
            return numero
            # raise Exception(u'Código extranjería debe tener como máximo 15 caracteres')

        if tipo == 'DNI' and len(numero) != 8:
            return numero
            # raise Exception(u'DNI sólo debe tener 8 caracteres')

        return numero

    def get_apellido_materno(self):
        if self.perfil_pago.prof_doc_type.upper() == 'FACTURA' and self.get_tipo_cliente == 'J':
            return ''
        else:
            if self.perfil_pago.prof_lastname_mother:
                return self.perfil_pago.prof_lastname_mother.upper()
            else:
                # print('Usted no ingreso el apellido materno')
                return '.'

    def get_apellido_paterno(self):
        if self.get_tipo_cliente == 'J':
            return ''
        else:
            if self.perfil_pago.prof_lastname:
                return self.perfil_pago.prof_lastname.upper()
            else:
                print('Usted no ingreso el apellido paterno')
                return ''

    def get_fecha_nacimiento(self):
        return ""

    def get_ec_nombres(self):
        if self.get_tipo_cliente == 'J':
            return ''
        else:
            return self.get_nombres()

    def get_nombres(self):
        if self.perfil_pago.prof_name:
            return self.perfil_pago.prof_name.upper()
        else:
            print('Usted no ingreso un nombre')
            return ''

    def get_sexo(self):
        return 'M'
        gender = self.perfil_pago.prof_genero.upper()[:1]
        return 'F' if gender == 'F' else 'M'

    def get_tipo_documento(self):
        # # Hacer la lógica cuando es factura
        return self.perfil_pago.prof_doc_type.upper() if self.perfil_pago.prof_doc_type else 'DNI'

    def get_tipo_cliente(self):
        tipo = self.get_tipo_documento()
        numero = self.get_numero_documento()

        if tipo == "RUC" and (numero.startswith('10') or numero.startswith('15')):
            # Facura cuando es persona natural
            return 'N'
        elif tipo == "DNI":
            return 'N'
        elif tipo == 'RUC':
            return 'J'

    def get_email(self):
        return self.perfil_pago.portal_email.lower()

    def get_siebel_name(self):
        if self.get_tipo_cliente == 'J':
            return self.get_nombres()
        else:
            return '%s %s, %s' % (
                self.get_apellido_paterno(),
                self.get_apellido_materno(),
                self.get_nombres()
            )


class SiebelSubscriptionSender(object):

    def __init__(self, operation, first_change_rate):
        self.operation = operation
        self.profile = operation.payment_profile
        self.product = operation.plan.product
        self.subscription = operation.payment.subscription
        self.first_change_rate = first_change_rate

    def send_subscription(self):
        message_plugin = LogPlugin(
            instance=self.operation,
            nsprefix='http://www.siebel.com/xml/ECO%20Order%20Entry%20(Sales)%20Lite',
            log_instance=LogSiebelOv(operation=self.operation)
        )
        client = SudsClient(
            settings.PAYWALL_SIEBEL_URL + 'wscrearov.asmx?wsdl',
            plugins=[message_plugin],
            cache=None
        )
        client.options.prettyxml = True
        CrearOV_Input = client.factory.create('ns0:CrearOV_Input')

        try:
            CrearOV_Input.ListOfEcoOrderEntrySalesLite2 = [
                {"OrderEntry-Orders": self.get_payment_data(self.operation)}
            ]

            response = client.service.CrearOV(CrearOV_Input)
            response = recursive_dict(response)

        except socket.error:
            capture_exception()

        except Exception:
            capture_exception()

        else:
            if 'IdDelivery' in response and response['IdDelivery']:
                self.operation.siebel_date = datetime.now()
                self.operation.siebel_state = True
                self.operation.siebel_delivery = response['IdDelivery']
                self.operation.save()

    def get_payment_data(self, paquete):
        return {
            'Account': self.profile.siebel_name,  # NameCliente
            'AccountIntegrationId': '',
            'CurrencyCode': 'PEN',
            'ECTipoOV': 'D',
            'ECTipoMotivoSuscripcion': 'VENTA',
            'IntegrationId': self.get_first_integration_id(),  # 1506
            'ListOfOrderEntry-LineItems': [
                {'OrderEntry-LineItems': self.get_line_items(paquete)}
            ],
            'ListOfPayments': [
                {'Payments': self.get_list_of_payments()}
            ],
            'OrderNumber': '',
            'OrderType': 'Pedido de ventas',
            'PaymentTerm': 'Contado',
            'PriceList': 'LISTA DE PRECIOS DIARIOS',
            'PrimaryOrganization': 'Default Organization',
            'Revision': 1,
            'ShipToAddress': self.operation.payment.payment_profile.siebel_direction,
        }

    def get_first_integration_id(self):
        return int(self.operation.id) + 50000000000

    def get_line_items(self, paquete):
        items = [self.get_line_item(number=1)]

        if self.get_component():
            dict_days = {'2': self.product.siebel_component, }

            for indice, day_code in dict_days.items():
                items.append(self.get_line_item(number=indice, code=day_code))
        return items

    def get_integration_id(self):
        if not hasattr(self, '_timestamp'):
            self._timestamp = str(time.time()).split('.')[0]
            self._id_index = 0
        else:
            self._id_index += 1

        return self._timestamp + str(self._id_index)

    def get_product(self):
        return self.product.siebel_name.upper() + ' - ' + str(self.product.siebel_code)
        # return "COMERCIO EJECUTIVO - 36148"  # quitar

    def get_line_item(self, number=1, code=''):
        # final_payment = self.subscription.data.get('paymentHistory')[-1]
        # period_from = timestamp_to_datetime(final_payment['periodFrom'])
        return {
            'BillingAccount': self.profile.siebel_name,  # NameCliente, cuando sea factura cambiara
            'BillingAccountId': '',
            'BillingIntegrationId': '',
            'BillToAddressName': '',
            'CurrencyCode': 'PEN',
            'Description2': '',
            'ECBillAccountPrimaryAddressName': self.profile.siebel_direction,
            'ECEjecutivoCuenta': 'PPROCESOS',
            'ECFacturaAutomaticoFlg': 'Y',
            'ECFormadeEntrega': 'DEBAJO DE PUERTA DE COCHERA'.upper(),  # enDuroPorqueEsDigital
            'ECFormadeEntregaEspecial': '',
            'ECGrupodeventas': '',
            'ECModoRenovacion': 'A Pedido',  # 'Automática'# verificar si habrá otro tipo: A Pedido
            'ECNumeroLote': '',  # self.operation.plan.
            'ECPeriodoFacturacion': self.periodo_facturacion(),  # 'Semestral', # self.operation.plan.plan_months,  # cambiar nombre de campo por periodo
            'ECPeriodoSuscripcion': self.periodo_facturacion(),  # 'Semestral', # self.operation.plan.plan_months,  # validar precio de introduccion
            'ECPlandeVenta': 'Portal_Paywall - 33',  # 'PORTAL WEB - 30',  # Asignar el origen nuevo para siebel
            'IntegrationId': self.get_integration_id(),
            'LineNumber': number,
            'LineNumber2': '',
            'NetPrice': self.get_netPrice(),  # self.operation.ope_amount,  # 176.27,
            'OrderHeaderId': '',
            'ParentOrderItemId': '',
            'ProdPromName': self.get_introduction_plan(),
            'Product': code if code else self.get_product(),  # COMERCIO EJECUTIVO - 36148
            'QuantityRequested': 1,
            'ServiceEndDate': '',
            'ServiceStartDate': self.get_date_subscription(),  # str(time.strftime("%m/%d/%Y"))
            'ShipToAccount': self.profile.siebel_name,
            'ShipToAddress': self.profile.siebel_direction,
        }

    def get_date_subscription(self, ):
        # obtiene la fecha de inicio de suscripcion mes/dia/año
        try:
            tz = timezone.get_current_timezone()

            if self.first_change_rate:
                date_subscription = self.operation.payment.date_payment
            else:
                date_subscription = self.operation.payment.subscription.starts_date

            date_subscription_local_time = date_subscription.astimezone(tz)
            return date_subscription_local_time.strftime("%m/%d/%Y")
        except Exception as e:
            print(e)
            return ''

    def get_component(self):
        try:
            return self.product.siebel_component
        except Exception:
            print('no esta declarado el componente')
            return ''

    def get_component_old(self):
        # rates = Rate.objects.filter(plan=self.operation.plan)
        # for rate_obj in rates:
        #     if rate_obj.state:
        #         if rate_obj.siebel_component:
        #             return rate_obj.siebel_component
        #
        # return ''
        pass

    # def get_netPrice(self):
    #     try:
    #         rate = Rate.objects.filter(plan=self.operation.plan, state=True).order_by('created').first()
    #         if rate.rate_neto:
    #             return rate.rate_neto
    #         else:
    #             print('no hay monto neto')
    #             return ''
    #     except Exception:
    #         print('no hay monto neto')
    #         return ''

    def get_netPrice(self):
        try:
            value = self.get_renovation_promotion()
            if value:
                # si continua con la promocion
                rates = Rate.objects.get(plan=self.operation.plan, state=True, type=1)
                return rates.rate_neto
            else:
                # ya no continua con la promocion
                rates = Rate.objects.get(plan=self.operation.plan, state=True, type=0)
                return rates.rate_neto
        except Exception as e:
            print(e)
            return ''

    def get_renovation_promotion(self):
        # define si se renovara la promocion o no
        # retorna 1 si se renovara la promocion
        # retorna 0  suscripción se renovara pero ya no tendrá promoción

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id).count()

        if len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
            if nro_recurrence <= self.operation.plan.data['rates'][0]['durationCount']:  # continua la promocion
                return 1
            else:
                return 0
        else:
            return 0

    def get_introduction_plan(self):
        rates = Rate.objects.filter(plan=self.operation.plan)
        siebel_code_promo = ''
        for rate_obj in rates:
            if rate_obj.siebel_code_promo:
                siebel_code_promo = rate_obj.siebel_code_promo

        return siebel_code_promo

        # rates = Rate.objects.filter(plan=self.operation.plan)
        # siebel_code_promo = ''
        # for rate_obj in rates:
        #     if rate_obj.state and rate_obj.type:   #promocion
        #         if rate_obj.siebel_code_promo:
        #             siebel_code_promo = rate_obj.siebel_code_promo
        #         else:
        #             siebel_code_promo = ''
        #         break
        # print('hi')
        # print(siebel_code_promo)
        # return siebel_code_promo

    def periodo_facturacion(self):
        plan = self.operation.plan
        if plan.data and plan.data.get('rates'):
            billing_frequency = plan.data['rates'][-1]['billingFrequency']
            dict_periodo = {'Month': 'Mensual', '6': 'Semestral', 'Year': 'Anual'}
            return dict_periodo.get(billing_frequency)

    def get_list_of_payments(self):
        return {
            'Payment': '',
            'PaymentDate': '',
            'PaymentMethod': 'Efectivo',
            'PaymentType': 'Pago'
        }


class SiebelConciliationSender(object):
    def __init__(self, operation):
        self.operation = operation
        self.subscription = operation.payment.subscription
        self.profile = operation.payment.payment_profile
        self.log_siebel_conciliacion = None

    def get_netPrice_old(self):
        rates = Rate.objects.filter(plan=self.operation.plan)
        total = 0
        for rate_obj in rates:
            if rate_obj.siebel_code_promo:
                return rate_obj.rate_total
            if rate_obj.type == 0:  # precio regular
                total = rate_obj.rate_total
        return total

    def get_netPrice_version_anterior(self):
        try:
            rates = Rate.objects.filter(plan=self.operation.plan, state=True)
            count = 1

            for rate_obj in rates:
                if count == self.get_nro_rate():
                    return rate_obj.rate_total
                count += 1
            print('No existe el orden del rate')
            return ''
        except Exception as e:
            print(e)
            return ''

    def get_netPrice(self):
        try:
            value = self.get_renovation_promotion()
            if value:
                # si continua con la promocion
                rates = Rate.objects.get(plan=self.operation.plan, state=True, type=1)
                return rates.rate_total
            else:
                # ya no continua con la promocion
                rates = Rate.objects.get(plan=self.operation.plan, state=True, type=0)
                return rates.rate_total
        except Exception as e:
            print(e)
            return ''

    def get_renovation_promotion(self):
        # define si se renovara la promocion o no
        # retorna 1 si se renovara la promocion
        # retorna 0  suscripción se renovara pero ya no tendrá promoción

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id,
                                                  payment__date_payment__lte=self.operation.payment.date_payment).count()

        if len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
            if nro_recurrence <= self.operation.plan.data['rates'][0]['durationCount']:  # continua la promocion
                return 1
            else:
                return 0
        else:
            return 0

    def get_promotion(self):
        # ve si va a continuar con la promocion: 1 continua con la promocion, 0 no
        try:
            rates = Rate.objects.filter(plan=self.operation.plan, state=True)
            count = 1

            for rate_obj in rates:
                if count == self.get_nro_rate():
                    return rate_obj.type
                count += 1
            print('No existe el rate')
            return ''
        except Exception as e:
            print(e)
            return ''

    def get_date_payment_renovation(self, date_payment):
        # obtiene la fecha de renovacion con formato 19/03/2020
        try:
            tz = timezone.get_current_timezone()
            date_payment_local_time = date_payment.astimezone(tz)
            return date_payment_local_time.strftime("%d/%m/%Y")
        except Exception as e:
            print(e)
            return ''

    def get_date_payment(self, date_payment):
        # obtiene la fecha de renovacion con formato 19/03/2020
        try:
            tz = timezone.get_current_timezone()
            date_payment_local_time = date_payment.astimezone(tz)
            return date_payment_local_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(e)
            return ''

    def renovar_suscripcion(self, cod_delivery, renovacion, type_conciliation):
        try:
            if not self.operation.recurrencia_response_state:
                print('ingresa?')
                dict_request = {
                    'cod_delivery': cod_delivery,
                    'renovacion': renovacion,
                    'fchIniRenovacion': self.get_date_payment_renovation(self.operation.payment.date_payment)
                }
                self.log_siebel_conciliacion.log_recurrence_request = dict_request
                url_renovacion = str(settings.PAYWALL_SIEBEL_IP) + '/wsSuscripcionesPaywall/renovar.suscripcion?codDelivery=' + \
                    str(cod_delivery) + '&valRenovacion=' + str(renovacion) + '&fchIniRenovacion=' + \
                                     self.get_date_payment_renovation(self.operation.payment.date_payment)
                PARAMS = {}
                r = requests.get(url=url_renovacion, params=PARAMS)
                data = r.json()
                self.log_siebel_conciliacion.log_recurrence_response = data
                self.log_siebel_conciliacion.type = type_conciliation

                self.operation.recurrencia_request = dict_request
                self.operation.recurrencia_response = data
                if str(data.get('response').get('respuesta', '')) == '1':
                    self.operation.recurrencia_response_state = True
                else:
                    self.operation.recurrencia_response_state = False
                return data
            else:
                print('Ya se registro la recurrencia')
                return ''
        except Exception:
            print('error en renovar suscripcion')
            capture_exception()
            return ''

    # obtiene la posicion de la operacion
    def get_nro_rate(self):
        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id, recurrencia_response_state=True).count()
        if not nro_recurrence:
            if Operation.objects.filter(payment__subscription__arc_id=arc_id).count():
                nro_recurrence = -1
        nro_recurrence += 2
        total_duration_count = 0
        if self.operation.plan.data['rates']:
            count = 1
            for data in self.operation.plan.data['rates']:
                total_duration_count = total_duration_count + data['durationCount']
                if nro_recurrence <= total_duration_count:  # continua la promocion
                    return count
                count += 1
            return 0
        else:
            print('No hay')
            return 0

    # def get_recurrence(self):
    #     arc_id = self.operation.payment.subscription.arc_id
    #     nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id, recurrencia_response_state=True).count()
    #     nro_recurrence += 2
    #     total_duration_count = 0
    #     if self.operation.plan.data['rates']:
    #         count = 1
    #         for data in self.operation.plan.data['rates']:
    #             total_duration_count = total_duration_count + data['durationCount']
    #             if nro_recurrence <= total_duration_count:  # continua la promocion
    #                 self.nro_rate = count
    #                 count += 1
    #                 return 1
    #
    #     else:
    #         print('No hay rates configurados')
    #     return 0

    def promotional_plan_free(self):
        obj_operation = Operation.objects.get(payment__subscription=self.subscription, payment__pa_origin='WEB')
        if obj_operation.ope_amount == 0:
            return True
        else:
            return False

    def first_rate_change(self):
        # retorna 1 si es el primer cambio de tarifa
        # retorna 0 si no es el primer cambio de tarifa

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id,
                                                  payment__date_payment__lte=self.operation.payment.date_payment).count()

        if len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
            first_change_rate = int(self.operation.plan.data['rates'][0]['durationCount']) + 1
            if nro_recurrence == first_change_rate:  # primer cambio de tarifa
                return 1
            else:
                return 0
        else:
            return 0

    def primer_cambio_de_tarifa(self):
        # define si se renovara la promocion o no
        # retorna 1 si se renovara la promocion
        # retorna 0  suscripción se renovara pero ya no tendrá promoción

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(payment__subscription__arc_id=arc_id).count()

        if len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
            first_change_rate = int(self.operation.plan.data['rates'][0]['durationCount']) + 1
            if nro_recurrence == first_change_rate:  # primer cambio de tarifa
                return 1
            else:
                return 0
            # elif nro_recurrence > first_change_rate and self.operation.envio_pago == '':
        else:
            return 0

    def send_conciliation(self):
        exist_transaction = FinancialTransaction.objects.filter(order_number=self.operation.payment.arc_order,
                                                                amount=self.operation.ope_amount).count()
        if exist_transaction:
            payu_ope = []
            self.log_siebel_conciliacion = LogSiebelConciliacion(operation=self.operation)

            if self.operation.payment.pa_origin == 'RECURRENCE':
                type_conciliation = 'recurrence'

                try:
                    if self.operation.siebel_delivery:
                        id_delivery = self.operation.siebel_delivery
                    else:
                        obj_operation = Operation.objects.get(payment__subscription=self.subscription,
                                                              siebel_delivery__isnull=False)
                        id_delivery = obj_operation.siebel_delivery
                    ente_code = self.profile.siebel_entecode
                    if ente_code and id_delivery:
                        print(str(self.operation.id) + 'renovacion')

                        if self.promotional_plan_free() and self.first_rate_change():
                            print('primer cambio de tarifa')
                        elif self.promotional_plan_free() and not self.first_rate_change():
                            self.renovar_suscripcion(id_delivery, 0, type_conciliation)
                        else:
                            self.renovar_suscripcion(id_delivery, self.get_renovation_promotion(), type_conciliation)

                        payu_ope = FinancialTransaction.objects.filter(order_number=self.operation.payment.arc_order,
                                                                       amount=self.operation.ope_amount)
                except Exception:
                    capture_exception()

            else:
                type_conciliation = 'web'
                id_delivery = self.operation.siebel_delivery
                if hasattr(self.profile, 'siebel_entecode'):
                    ente_code = self.profile.siebel_entecode
                else:
                    ente_code = ''
                payu_ope = FinancialTransaction.objects.filter(order_number=self.operation.payment.arc_order,
                                                               amount=self.operation.ope_amount)
            try:
                final_payment = self.subscription.data.get('paymentHistory')[-1]
                period_from = timestamp_to_datetime(final_payment['periodFrom'])
                for payu_obj in payu_ope:
                    if self.get_netPrice():
                        xdata = {
                            'tem:cod_ente': ente_code,
                            'tem:cod_suscripcion': id_delivery,  # id_delivery, siebel_delivery
                            'tem:monto_cobrado': self.get_netPrice(),  # self.operation.ope_amount,
                            'tem:num_operacion': payu_obj.order_id,  # self.operation.payment.payu_order,  # payu_orderid
                            'tem:fch_hra_cobro': self.get_date_payment(self.operation.payment.date_payment),
                            'tem:num_liquida_id': payu_obj.transaction_id,
                            'tem:medio_de_pago': self.operation.payment.pa_method
                        }

                        if id_delivery and ente_code:
                            print(str(self.operation.id) + 'pago')
                            xml = soap_utils.soap.prepareConciliacion({'xdata': xdata})
                            response = soap_utils.soap.sendConciliacion(xml)
                            self.operation.conciliation_siebel_request = xml
                            self.operation.conciliation_siebel_response = response
                            self.operation.conciliation_cod_response = response.get('Cod_Response', '')
                            self.operation.rate_total_sent_conciliation = self.get_netPrice()
                            if not self.operation.conciliation_siebel_hits:
                                self.operation.conciliation_siebel_hits = 1
                            else:
                                self.operation.conciliation_siebel_hits += 1
                            self.operation.save()

                            self.log_siebel_conciliacion.log_request = xml
                            self.log_siebel_conciliacion.log_response = response
                            if type_conciliation:
                                self.log_siebel_conciliacion.type = type_conciliation
                            self.log_siebel_conciliacion.save()
                        else:
                            print('no existe ente_code y siebel_delivery')
            except Exception:
                capture_exception()

    def send_conciliation_recurrence(self):
        payu_ope = []
        self.log_siebel_conciliacion = LogSiebelConciliacion(operation=self.operation)

        if self.operation.payment.pa_origin == 'RECURRENCE':
            print('recurrence')
            type_conciliation = 'recurrence'

            try:
                payment = Payment.objects.get(
                    subscription=self.subscription,
                    pa_origin='WEB'
                )
                operations = Operation.objects.get(payment=payment)
                id_delivery = operations.siebel_delivery
                ente_code = payment.payment_profile.siebel_entecode
                # self.renovar_suscripcion(
                #   id_delivery, self.get_renovation_promotion(), type_conciliation)
                payu_ope = FinancialTransaction.objects.filter(
                    order_number=self.operation.payment.arc_order,
                    amount=self.operation.ope_amount
                )
            except Exception:
                capture_exception()

        else:
            print('web')
            type_conciliation = 'web'
            id_delivery = self.operation.siebel_delivery
            if hasattr(self.profile, 'siebel_entecode'):
                ente_code = self.profile.siebel_entecode
            else:
                ente_code = ''
            payu_ope = FinancialTransaction.objects.filter(
                order_number=self.operation.payment.arc_order,
                amount=self.operation.ope_amount
            )

        try:
            final_payment = self.subscription.data.get('paymentHistory')[-1]
            period_from = timestamp_to_datetime(final_payment['periodFrom'])
            for payu_obj in payu_ope:
                if self.get_netPrice():
                    xdata = {
                        'tem:cod_ente': ente_code,
                        'tem:cod_suscripcion': id_delivery,  # id_delivery, siebel_delivery
                        'tem:monto_cobrado': self.get_netPrice(),  # self.operation.ope_amount,
                        'tem:num_operacion': payu_obj.order_id,  # self.operation.payment.payu_order,  # payu_orderid
                        'tem:fch_hra_cobro': period_from.strftime("%Y-%m-%d %H:%M:%S"),
                        'tem:num_liquida_id': payu_obj.transaction_id,
                        'tem:medio_de_pago': self.operation.payment.pa_method
                    }

                    if id_delivery and ente_code:
                        xml = soap_utils.soap.prepareConciliacion({'xdata': xdata})
                        response = soap_utils.soap.sendConciliacion(xml)
                        self.operation.conciliation_siebel_request = xml
                        self.operation.conciliation_siebel_response = response
                        self.operation.conciliation_cod_response = response.get('Cod_Response', '')
                        self.operation.rate_total_sent_conciliation = self.get_netPrice()
                        if not self.operation.conciliation_siebel_hits:
                            self.operation.conciliation_siebel_hits = 1
                        else:
                            self.operation.conciliation_siebel_hits += 1
                        self.operation.save()

                        self.log_siebel_conciliacion.log_request = xml
                        self.log_siebel_conciliacion.log_response = response
                        if type_conciliation:
                            self.log_siebel_conciliacion.type = type_conciliation
                        self.log_siebel_conciliacion.save()
                    else:
                        print('no existe ente_code y siebel_delivery')

        except Exception:
            capture_exception()
