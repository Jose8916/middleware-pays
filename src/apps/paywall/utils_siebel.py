from datetime import datetime, timedelta
import socket
import time
from django.utils import formats, timezone
from django.conf import settings
from django.utils.timezone import get_default_timezone
from sentry_sdk import capture_exception, capture_event, push_scope
from suds.bindings import binding
from suds.client import Client as SudsClient
from suds.plugin import MessagePlugin
from suds.sudsobject import asdict
import requests

from .utils import current_time
from apps.arcsubs.utils import timestamp_to_datetime
from apps.paywall import soap_utils
from apps.paywall.models import FinancialTransaction, Payment, Operation
from apps.siebel.models import Rate, LogSiebelClient, LogSiebelOv, LogSiebelConciliacion, PendingSendSiebel, SiebelConfirmationPayment


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

    def __init__(self, instance, nsprefix, log_instance=None, log_transaction=None):
        self.instance = instance
        self.nsprefix = nsprefix
        self.log_instance = log_instance
        self.log_transaction = log_transaction

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

            if self.log_transaction:
                try:
                    self.log_transaction.log_response = context.reply
                    # payu_ope = FinancialTransaction.objects.get(order_number=self.instance.payment.arc_order)
                    self.log_transaction.transaction_id = self.instance.payment.payment_financial_transaction.transaction_id
                    self.log_transaction.save()
                except Exception:
                    capture_exception()

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

        except socket.error as e:
            capture_exception()
            return {'socket error': e}

        except Exception as e:
            capture_exception()
            return {'error desconocido': e}
        else:
            if 'EnteCliente' in result and result['EnteCliente']:
                self.perfil_pago.siebel_name = result['NameCliente']
                self.perfil_pago.siebel_entecode = result['EnteCliente']
                self.perfil_pago.siebel_entedireccion = result['EnteDireccion']
                self.perfil_pago.siebel_direction = result['Nombre_spcDireccion']
                self.perfil_pago.siebel_date = current_time()
                self.perfil_pago.save()

            if not result['EnteCliente']:
                return {'No creo entecode': result}
            if result['EnteDireccion']:
                return {'No creo entedireccion': result}

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
        if self.perfil_pago.prof_doc_type == 'OTRO':
            return 'OTR'
        elif self.perfil_pago.prof_doc_type:
            return self.perfil_pago.prof_doc_type.upper()
        else:
            return ''

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

    def __init__(self, operation, first_change_rate, log_transactions):
        self.operation = operation
        self.profile = operation.payment_profile
        self.product = operation.plan.product
        self.subscription = operation.payment.subscription
        self.first_change_rate = first_change_rate
        self.log_transactions = log_transactions

    def send_subscription(self):
        if self.log_transactions:
            save_log_transaction = PendingSendSiebel()
        else:
            save_log_transaction = None

        message_plugin = LogPlugin(
            instance=self.operation,
            nsprefix='http://www.siebel.com/xml/ECO%20Order%20Entry%20(Sales)%20Lite',
            log_instance=LogSiebelOv(operation=self.operation),
            log_transaction=save_log_transaction
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
                self.subscription.delivery = response['IdDelivery']
                self.subscription.save()
                print('delivery creada: ' + str(response['IdDelivery']))
                if self.log_transactions:
                    self.log_transactions.ov = 'enviado'
            else:
                if self.log_transactions:
                    self.log_transactions.ov = 'no enviado'

    def get_payment_data(self, paquete):
        return {
            'AccountIntegrationId': self.profile.siebel_entecode,
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
        lista = ['48333', '48268', '48334', '48336', '48376', '48374', '48357', '48375', '46235', '46181', '48426',
                 '46205', '46274', '46223', '46384', '46276', '46288', '46234', '46333', '46383', '46335', '46352',
                 '46407', '46410', '46411', '46430', '46429', '46470', '46432', '46469', '46435', '46488', '46506',
                 '46552', '46508', '46531', '46353', '46436', '46600', '46289', '46180', '46224', '46291', '46572',
                 '46632', '46603', '46604', '46692', '46799', '46651', '46666', '46667', '46668', '46704', '46910',
                 '46775', '46934', '46935', '46979', '46797', '46848', '46991', '47040', '47005', '47145', '47059',
                 '47085', '47117', '47116', '47119', '47247', '47369', '47378', '47558', '47367', '47427', '47417',
                 '47446', '47469', '47529', '47534', '47670', '47876', '47581', '47686', '47761', '47817', '47743',
                 '47816', '47851', '47941', '47942', '47966', '47899', '47987', '48063', '47988', '47990', '48016',
                 '48050', '48061', '48062', '48064', '47965', '48033', '48091', '48092', '48131', '48154', '48085',
                 '48158', '48186', '48189', '48229', '48264']

        if self.operation.id in lista:
            return int(self.operation.id) + 50000000000
        else:
            return int(self.operation.id) + 20000000000

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
        try:
            return self.product.siebel_name.upper() + ' - ' + str(self.product.siebel_code)
        except Exception:
            capture_exception()
            return ''
        # return "COMERCIO EJECUTIVO - 36148"  # quitar

    def get_line_item(self, number=1, code=''):
        return {
            'BillingIntegrationId': self.profile.siebel_entecode,
            'ShipToAccountIntegrationId': self.profile.siebel_entecode,
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

    def get_netPrice(self):
        try:
            rate_obj = Rate.objects.get(plan=self.operation.plan, state=True, type=2)  # 2 es para promocion indefinida
            if rate_obj:
                return rate_obj.rate_neto
        except Exception:
            pass

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
            with push_scope() as scope:
                scope.set_tag("id_operation", self.operation.id)
                scope.level = 'warning'
                capture_event(
                    {
                        'message': 'get_net_price_error',
                        'extra': {
                            'plan': self.operation.plan.id,
                            'renovation_promotion': value,
                            'rate': rates,
                            'error': e
                        }
                    }
                )
            return ''

    def get_renovation_promotion(self):  # para ov
        """
            Define si se renovara la promocion o no
                retorna 1: si se renovara la promocion
                retorna 0: suscripción se renovara pero ya no tendrá promoción
        """

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(
            payment__subscription__arc_id=arc_id,
            payment__date_payment__lte=self.operation.payment.date_payment
        ).count()

        try:
            rate_obj = Rate.objects.get(plan=self.operation.plan, type=1)  # 1 es para promocion
            rate_duration = rate_obj.duration
        except Exception:
            rate_duration = None

        if rate_duration:
            if nro_recurrence <= rate_duration:
                return rate_obj.siebel_code_promo
            else:
                return ''
        else:
            if len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
                if nro_recurrence <= self.operation.plan.data['rates'][0]['durationCount']:  # continua la promocion
                    return rate_obj.siebel_code_promo
                else:
                    return ''
            else:
                return ''

    def get_introduction_plan(self):
        try:
            rates = Rate.objects.filter(plan=self.operation.plan)

            if self.with_promotion(rates):  # con promoción excepto la promo indefinida
                return self.get_renovation_promotion()
            else:
                #  Directo, sin promocion solo tiene la tarifa regular o promo indefinida
                for rate_obj in rates:
                    if rate_obj.siebel_code_promo:
                        return rate_obj.siebel_code_promo
                    else:
                        return ''
        except Exception:
            capture_exception()
            return ''

    def with_promotion(self, rates):  # excepto la promo indefinida
        try:
            for rate_obj in rates:
                if rate_obj.type == 1 and rate_obj.duration != 100:  #100 es el valor para la promocion indefinida
                    return True
            return False
        except Exception:
            return False

    def periodo_facturacion(self):
        plan = self.operation.plan
        periodo_de_facturacion = ''

        try:
            rate_obj = Rate.objects.filter(plan=self.operation.plan).first()
            if rate_obj.get_billing_frequency_display():
                periodo_de_facturacion = rate_obj.get_billing_frequency_display()
        except Exception:
            periodo_de_facturacion = ''

        if periodo_de_facturacion:
            return periodo_de_facturacion
        elif plan.data and plan.data.get('rates'):
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
    def __init__(self, operation, test_mode):
        self.operation = operation
        self.subscription = operation.payment.subscription
        self.profile = operation.payment.payment_profile
        self.log_siebel_conciliacion = None
        self.test_mode = test_mode

    def get_netPrice(self):
        try:
            rate_obj = Rate.objects.get(plan=self.operation.plan, state=True, type=2)  # 2 es para promocion indefinida
            if rate_obj:
                return rate_obj.rate_total
        except Exception:
            pass

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

    def get_renovation_promotion(self):  # para conciliacion
        # define si se renovara la promocion o no
        # retorna 1 si se renovara con
        # la promocion
        # retorna 0  suscripción se renovara pero ya no tendrá promoción

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(
            payment__subscription__arc_id=arc_id,
            payment__date_payment__lte=self.operation.payment.date_payment
        ).count()

        try:
            rate_obj = Rate.objects.get(plan=self.operation.plan, type=1)  # 1 es para promocion
            duration_rate = rate_obj.duration
        except Exception:
            duration_rate = None

        if duration_rate:
            if nro_recurrence <= duration_rate:
                return 1
            else:
                return 0
        else:
            if len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
                if nro_recurrence <= self.operation.plan.data['rates'][0]['durationCount']:  # continua la promocion
                    return 1
                else:
                    return 0
            else:
                return 0

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

    def renovar_suscripcion(self, cod_delivery, renovacion, type_conciliation, num_liquidacion, period_from, period_to):
        """
        renovacion = 1, quiere decir que la suscripcion se debe renovar y mantener la promocion
        renovacion = 0, quiere decir que la suscripcion se debe renovar pero ya no tendra promocion
        """
        if period_from and period_to and not self.operation.recurrencia_response_state:
            dict_request = {
                'cod_delivery': cod_delivery,
                'renovacion': renovacion,
                'fchIniRenovacion': period_from,
                'num_liquidacion': num_liquidacion,
                'fchFinRenovacion': period_to
            }
            self.log_siebel_conciliacion.log_recurrence_request = dict_request
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
                    r = requests.get(url=url_renovacion, params=PARAMS)
                    data = r.json()
                except Exception as e:
                    print(e)
                    print('error en renovar suscripcion')
                    capture_exception()
                else:
                    self.operation.recurrencia_request = dict_request
                    self.operation.recurrencia_response = data
                    if str(data.get('response').get('respuesta', '')) == '1':
                        self.operation.recurrencia_response_state = True
                    else:
                        self.operation.recurrencia_response_state = False

                    if not self.operation.conciliation_siebel_hits:
                        self.operation.conciliation_siebel_hits = 1
                    else:
                        self.operation.conciliation_siebel_hits += 1
                    self.operation.save()
                    print('Renovacion enviada: ' + str(self.operation.id))

                try:
                    self.log_siebel_conciliacion.log_recurrence_response = data
                    self.log_siebel_conciliacion.type = type_conciliation
                    self.log_siebel_conciliacion.save()
                except:
                    pass
        else:
            print('Ya se registro la recurrencia: {operation_id}'.format(operation_id=str(self.operation.id)))
            return ''

    def promotional_plan_free(self):
        obj_operation = Operation.objects.get(payment__subscription=self.subscription, payment__pa_origin='WEB')
        if obj_operation.ope_amount == 0:
            return True
        else:
            return False

    def indefinite_promotion(self):
        try:
            rate_obj = Rate.objects.get(plan=self.operation.plan, type=2)  # 1 es para promocion Indefinida
            if rate_obj:
                return True
            else:
                return False
        except Exception:
            return False

    def first_rate_change(self):
        # retorna 1 si es el primer cambio de tarifa
        # retorna 0 si no es el primer cambio de tarifa

        arc_id = self.operation.payment.subscription.arc_id
        nro_recurrence = Operation.objects.filter(
            payment__subscription__arc_id=arc_id,
            payment__date_payment__lte=self.operation.payment.date_payment
        ).count()

        try:
            rate_obj = Rate.objects.get(plan=self.operation.plan, type=1)  # 1 es para promocion
            duration_rate = int(rate_obj.duration) + 1
        except Exception:
            duration_rate = None

        if duration_rate:
            if nro_recurrence == duration_rate:
                return 1
            else:
                return 0
        elif len(self.operation.plan.data['rates']) > 1:  # valida si hay promocion en el plan
            first_change_rate = int(self.operation.plan.data['rates'][0]['durationCount']) + 1
            if nro_recurrence == first_change_rate:  # primer cambio de tarifa
                return 1
            else:
                return 0
        else:
            return 0

    def send_conciliation(self, confirmation_payment):
        try:
            payu_obj = FinancialTransaction.objects.get(
                order_number=self.operation.payment.arc_order,
                amount=self.operation.ope_amount,
                transaction_type='Payment'
            )
        except:
            payu_obj = None

        if payu_obj:
            payu_ope = []
            self.log_siebel_conciliacion = LogSiebelConciliacion(operation=self.operation)
            id_delivery = self.operation.payment.subscription.delivery
            ente_code = self.profile.siebel_entecode

            if self.operation.payment.pa_origin == 'RECURRENCE':
                type_conciliation = 'recurrence'
            else:
                type_conciliation = 'web'

            try:
                response_conciliation = self.operation.conciliation_cod_response.strip()
            except:
                response_conciliation = ''

            try:
                if payu_obj and id_delivery and ente_code:
                    if self.get_netPrice() and response_conciliation != '1':
                        xdata = {
                            'tem:cod_ente': ente_code,
                            'tem:cod_suscripcion': id_delivery,  # id_delivery, siebel_delivery
                            'tem:monto_cobrado': self.get_netPrice(),  # self.operation.ope_amount,
                            'tem:num_operacion': payu_obj.order_id,  # self.operation.payment.payu_order,  # payu_orderid
                            'tem:fch_hra_cobro': self.get_date_payment(self.operation.payment.date_payment),
                            'tem:num_liquida_id': payu_obj.transaction_id,
                            'tem:medio_de_pago': self.operation.payment.pa_method,
                            'tem:cod_pasarelaPago': 1,
                            'tem:nro_renovacion': confirmation_payment.nro_renovacion,
                            'tem:folio': confirmation_payment.folio_sunat,
                            'tem:cod_interno': confirmation_payment.cod_interno_comprobante
                        }

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
                        print(str(self.operation.id) + ' pago enviado')
                else:
                    print('No hay payu_obj o id_delivery o ente_code, operacion Id: ' + str(self.operation.id))

            except Exception as e:
                with push_scope() as scope:
                    scope.set_tag("id_subscription", self.subscription.arc_id)
                    scope.set_tag("order_number", self.operation.payment.arc_order)
                    scope.level = 'warning'
                    capture_event(
                        {
                            'message': 'payment_not_send',
                            'extra': {
                                'id_subscription': self.subscription.arc_id,
                                'finantial_transaction': payu_ope,
                                'error': e
                            }
                        }
                    )

    def format_local_date(self, date_str):
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            tz = timezone.get_current_timezone()
            date_payment_local_time = date_obj.astimezone(tz)
            date_payment_local_time = date_payment_local_time - timedelta(hours=5)
            return date_payment_local_time.strftime("%d/%m/%Y")
        except:
            return ''

    def send_payment(self):
        try:
            payu_ope = FinancialTransaction.objects.get(
                order_number=self.operation.payment.arc_order,
                amount=self.operation.ope_amount,
                transaction_type='Payment'
            )
        except:
            payu_ope = None

        if payu_ope:
            self.log_siebel_conciliacion = LogSiebelConciliacion(operation=self.operation)
            type_conciliation = 'recurrence'
            id_delivery = self.operation.payment.subscription.delivery
            ente_code = self.profile.siebel_entecode
            num_liquidacion = payu_ope.transaction_id
            period_from = self.format_local_date(payu_ope.data.get('periodFrom'))
            period_to = self.format_local_date(payu_ope.data.get('periodTo'))

            try:
                response_conciliation = self.operation.conciliation_cod_response.strip()
            except:
                response_conciliation = ''

            if period_from and ente_code and id_delivery and num_liquidacion and self.get_netPrice() \
                    and response_conciliation != '1' and not self.operation.recurrencia_response_state:
                if self.indefinite_promotion():
                    self.renovar_suscripcion(id_delivery, 1, type_conciliation, num_liquidacion, period_from, period_to)
                elif self.promotional_plan_free() and self.first_rate_change():
                    print('primer cambio de tarifa')
                elif self.promotional_plan_free() and not self.first_rate_change():
                    """
                        def renovar_suscripcion(self, cod_delivery, renovacion, type_conciliation)
                        renovacion = 1, quiere decir que la suscripcion se debe renovar y mantiene la promocion
                        renovacion = 0, quiere decir que la suscripcion se debe renovar pero ya no tendra promocion
                    """
                    self.renovar_suscripcion(id_delivery, 0, type_conciliation, num_liquidacion, period_from, period_to)
                else:
                    self.renovar_suscripcion(id_delivery, self.get_renovation_promotion(), type_conciliation, num_liquidacion, period_from, period_to)

                if not self.operation.conciliation_siebel_hits:
                    self.operation.conciliation_siebel_hits = 1
                else:
                    self.operation.conciliation_siebel_hits += 1
                self.operation.save()

                self.log_siebel_conciliacion.type = 'recurrence'
                self.log_siebel_conciliacion.save()
            else:
                print('Delivery o entecode No encontrado')

    def send_payment_faltantes(self):
        try:
            payu_ope = FinancialTransaction.objects.get(
                order_number=self.operation.payment.arc_order,
                amount=self.operation.ope_amount,
                transaction_type='Payment'
            )
        except Exception:
            payu_ope = None

        if payu_ope:
            self.log_siebel_conciliacion = LogSiebelConciliacion(operation=self.operation)
            type_conciliation = 'recurrence'
            id_delivery = self.operation.payment.subscription.delivery
            ente_code = self.profile.siebel_entecode
            num_liquidacion = payu_ope.transaction_id
            period_from = self.format_local_date(payu_ope.data.get('periodFrom'))
            period_to = self.format_local_date(payu_ope.data.get('periodTo'))

            if ente_code and id_delivery and num_liquidacion and self.get_netPrice():
                if self.indefinite_promotion():
                    self.renovar_suscripcion(id_delivery, 1, type_conciliation, num_liquidacion, period_from, period_to)
                elif self.promotional_plan_free() and self.first_rate_change():
                    print('primer cambio de tarifa')
                elif self.promotional_plan_free() and not self.first_rate_change():
                    """
                        def renovar_suscripcion(self, cod_delivery, renovacion, type_conciliation)
                        renovacion = 1, quiere decir que la suscripcion se debe renovar y mantiene la promocion
                        renovacion = 0, quiere decir que la suscripcion se debe renovar pero ya no tendra promocion
                    """
                    self.renovar_suscripcion(id_delivery, 0, type_conciliation, num_liquidacion, period_from, period_to)
                else:
                    self.renovar_suscripcion(id_delivery, self.get_renovation_promotion(), type_conciliation,
                                             num_liquidacion, period_from, period_to)


            else:
                print('Delivery o entecode No encontrado')

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
