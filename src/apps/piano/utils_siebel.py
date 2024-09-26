from datetime import datetime
import socket
import time
from django.utils import formats, timezone
from django.conf import settings
from django.utils.timezone import get_default_timezone
from apps.piano.constants import LIST_EMAIL_SENDER
from apps.paywall.shortcuts import render_send_email
from apps.paywall.models import Partner
from sentry_sdk import capture_exception, capture_event, push_scope
from suds.bindings import binding
from suds.client import Client as SudsClient
from suds.plugin import MessagePlugin
from suds.sudsobject import asdict
import requests

from apps.paywall.utils import current_time
from apps.arcsubs.utils import timestamp_to_datetime
from apps.piano.utils.utils_functions import get_list_amount_payment
from apps.paywall import soap_utils
from apps.paywall.models import FinancialTransaction, Payment, Operation
from apps.siebel.models import Rate, LogSiebelClient, LogSiebelOvPE, LogSiebelPaymentPiano, PendingSendSiebel, \
    SiebelConfirmationPayment, LogSiebelOvPiano
from apps.piano.models import SaleOrderPiano, PaymentPiano, PromotionTerm, PromotionPiano

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

    def __init__(self, instance, instance_sale_order, nsprefix, log_instance=None):
        self.instance = instance
        self.instance_sale_order = instance_sale_order
        self.nsprefix = nsprefix
        self.log_instance = log_instance

    def sending(self, context):
        request = context.envelope.decode('UTF-8')
        self.instance_sale_order.siebel_request = request
        self.instance_sale_order.save()
        self.log_instance.log_request = request
        self.log_instance.save()

    def received(self, context):
        response = context.reply
        if not self.instance_sale_order:
            self.instance_sale_order.siebel_hits = 1
        else:
            self.instance_sale_order.siebel_hits += 1

        self.instance_sale_order.siebel_response = context.reply
        self.instance_sale_order.save()
        self.log_instance.log_response = context.reply
        self.log_instance.save()

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
    def __init__(self, operation, subscription, test_mode, brand):
        self.operation = operation
        self.profile = operation.subscription.payment_profile
        self.product = operation.term.product
        self.subscription = subscription
        self.siebel_sale_order = operation.siebel_sale_order if operation.siebel_sale_order else SaleOrderPiano()
        self.test_mode = test_mode
        self.brand = brand

    def send_subscription(self):
        delivery_error = None
        if self.test_mode:
            print(self.get_payment_data(self.operation))
        else:
            message_plugin = LogPlugin(
                instance=self.operation,
                instance_sale_order=self.siebel_sale_order,
                nsprefix='http://www.siebel.com/xml/ECO%20Order%20Entry%20(Sales)%20Lite',
                log_instance=LogSiebelOvPiano(transaction=self.operation)
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
                print(response)
            except socket.error:
                print(socket.error)
                print('uno')
                capture_exception()

            except Exception as e:
                print(e)
                print('dos')
                capture_exception()

            else:
                if 'IdDelivery' in response and response.get('IdDelivery', None):
                    self.siebel_sale_order.delivery = response.get('IdDelivery', None)
                    self.siebel_sale_order.save()
                else:
                    delivery_error = self.operation.payu_transaction_id

                if response.get('IdDelivery', None):
                    subscription_obj = self.operation.subscription
                    subscription_obj.delivery = response.get('IdDelivery', None)
                    subscription_obj.save()

                self.operation.siebel_sale_order = self.siebel_sale_order
                self.operation.save()
        return delivery_error

    def get_payment_data(self, operation):
        return {
            'AccountIntegrationId': self.profile.siebel_entecode,
            'CurrencyCode': 'PEN',
            'ECTipoOV': 'D',
            'ECTipoMotivoSuscripcion': 'VENTA',
            'IntegrationId': self.get_first_integration_id(),  # 1506
            'ListOfOrderEntry-LineItems': [
                {'OrderEntry-LineItems': self.get_line_items(operation)}
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
            'ShipToAddress': self.profile.siebel_direction,
        }

    def get_first_integration_id(self):
        return int(self.operation.id) + 3000000000000

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
            'CurrencyCode': 'PEN',
            'Description2': '',
            'ECBillAccountPrimaryAddressName': self.profile.siebel_direction,
            'ECEjecutivoCuenta': 'PPROCESOS',
            'ECFacturaAutomaticoFlg': 'Y',
            'ECFormadeEntrega': 'DEBAJO DE PUERTA DE COCHERA'.upper(),  # enDuroPorqueEsDigital
            'ECFormadeEntregaEspecial': '',
            'ECGrupodeventas': '',
            'ECModoRenovacion': 'A Pedido',  # 'Automática'# verificar si habrá otro tipo: A Pedido
            'ECNumeroLote': '',
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
            'ShipToAccountIntegrationId': self.profile.siebel_entecode,
            'ShipToAddress': self.profile.siebel_direction,
        }

    def get_date_subscription(self, ):
        # obtiene la fecha de inicio de suscripcion mes/dia/año
        try:
            tz = timezone.get_current_timezone()
            date_time_obj = datetime.strptime(self.operation.access_from, '%m/%d/%Y')
            date_subscription_local_time = date_time_obj.astimezone(tz)
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
        if self.operation.original_price:
            if self.original_price(self.operation.original_price) and \
                    self.operation.amount != int(self.original_price(self.operation.original_price)):
                # ----------- log mensaje-----------
                try:
                    partner = Partner.objects.get(partner_code=self.operation.brand)
                except Exception:
                    partner = None
                if partner:
                    from_email = '{name_sender} <{direction_sender}>'.format(
                        name_sender=partner.partner_name,
                        direction_sender=partner.transactional_sender
                    )
                else:
                    from_email = None

                render_send_email(
                    template_name='mailings/error.html',
                    subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Error en el pago',
                    to_emails=LIST_EMAIL_SENDER,
                    from_email=from_email,
                    context={
                        'error': 'transaccion con promocion enviada get_netPrice: ' + self.operation.external_tx_id,
                    }
                )
                print('Ingresa a la promocion' + self.operation.external_tx_id)
                #----------- log mensaje-----------
                if PromotionPiano.objects.filter(subscription=self.operation.subscription).exists():
                    promotion_piano = PromotionPiano.objects.get(subscription=self.operation.subscription)
                    promotion = PromotionTerm.objects.get(
                        term=self.operation.term,
                        promotion_id=promotion_piano.promotion_id
                    )
                    return promotion.net_price_first_payment

        try:
            return self.operation.term.net_price_first_payment
        except Exception:
            return 0

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

    def original_price(self, original_price):
        try:
            original_price_ = original_price.split('PEN')
            return int(float(original_price_[1]))
        except:
            return ''

    def get_introduction_plan(self):
        if self.operation.original_price:
            if self.original_price(self.operation.original_price) and \
                    self.operation.amount != int(self.original_price(self.operation.original_price)):

                # ----------- log mensaje-----------
                try:
                    partner = Partner.objects.get(partner_code=self.operation.brand)
                except Exception:
                    partner = None
                if partner:
                    from_email = '{name_sender} <{direction_sender}>'.format(
                        name_sender=partner.partner_name,
                        direction_sender=partner.transactional_sender
                    )
                else:
                    from_email = None

                render_send_email(
                    template_name='mailings/error.html',
                    subject=('[Test]' if settings.ENVIRONMENT == 'test' else '[Production]') + ' Error en el pago',
                    to_emails=LIST_EMAIL_SENDER,
                    from_email=from_email,
                    context={
                        'error': 'transaccion con promocion enviada get_introduction_plan: ' + self.operation.external_tx_id,
                    }
                )
                print('Ingresa a la promocion' + self.operation.external_tx_id)
                # ----------- log mensaje-----------

                if PromotionPiano.objects.filter(subscription=self.operation.subscription).exists():
                    promotion_piano = PromotionPiano.objects.get(subscription=self.operation.subscription)
                    promotion = PromotionTerm.objects.get(
                        term=self.operation.term,
                        promotion_id=promotion_piano.promotion_id
                    )
                    return promotion.siebel_code_promo

        try:
            return self.operation.term.siebel_code_promo
        except Exception:
            return ''

    def periodo_facturacion(self):
        plan = self.operation.term
        return plan.get_period_display()

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
        #self.subscription = operation.subscription
        self.product = operation.term.product
        self.profile = operation.subscription.payment_profile
        self.log_siebel_conciliacion = None
        self.siebel_payment = operation.siebel_payment if operation.siebel_payment else PaymentPiano()

    def get_date_payment(self, operation):
        # obtiene la fecha de renovacion con formato 19/03/2020
        try:
            date_payment = operation.payment_date
            tz = timezone.get_current_timezone()
            date_payment_local_time = date_payment.astimezone(tz)
            return date_payment_local_time.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            print(e)
            return ''

    def send_conciliation(self, confirmation_payment, test_mode):
        payu_ope = []
        self.log_siebel_conciliacion = LogSiebelPaymentPiano(transaction=self.operation)
        id_delivery = self.operation.subscription.delivery
        ente_code = self.profile.siebel_entecode

        try:
            xdata = {
                'tem:cod_ente': ente_code,
                'tem:cod_suscripcion': id_delivery,  # id_delivery, siebel_delivery
                'tem:monto_cobrado': format(self.operation.amount, ".2f"),
                'tem:num_operacion': self.operation.payu_order_id,
                'tem:fch_hra_cobro': self.get_date_payment(self.operation),
                'tem:num_liquida_id': self.operation.payu_transaction_id,
                'tem:medio_de_pago': self.operation.payment_source_type,
                'tem:cod_pasarelaPago': 1,
                'tem:nro_renovacion': confirmation_payment.nro_renovacion,
                'tem:folio': confirmation_payment.folio_sunat,
                'tem:cod_interno': confirmation_payment.cod_interno_comprobante
            }
            if test_mode:
                print(xdata)
            else:
                xml = soap_utils.soap.prepareConciliacion({'xdata': xdata})
                response = soap_utils.soap.sendConciliacion(xml)
                ########### save payment ############################3
                self.siebel_payment.siebel_request = xml
                self.siebel_payment.siebel_response = response
                self.siebel_payment.cod_response = True if response.get('Cod_Response', '') else False
                if not self.siebel_payment.siebel_hits:
                    self.siebel_payment.siebel_hits = 1
                else:
                    self.siebel_payment.siebel_hits += 1
                self.siebel_payment.save()
                ########### end save payment ############################3
                self.operation.siebel_payment = self.siebel_payment
                self.operation.save()

                self.log_siebel_conciliacion.log_request = xml
                self.log_siebel_conciliacion.log_response = response
                self.log_siebel_conciliacion.save()
                print(self.operation.payu_transaction_id)
                if not response.get('Cod_Response', ''):
                    return {self.operation.payu_transaction_id: response}

        except Exception as e:
            print(e)
            with push_scope() as scope:
                scope.set_tag("external_tx_id", self.operation.external_tx_id)
                scope.level = 'warning'
                capture_event(
                    {
                        'message': 'payment_not_send',
                        'extra': {
                            'external_tx_id': self.operation.external_tx_id,
                            'error': e
                        }
                    }
                )

    def send_conciliation_without_vouchers(self, confirmation_payment, test_mode):
        payu_ope = []
        self.log_siebel_conciliacion = LogSiebelPaymentPiano(transaction=self.operation)
        id_delivery = self.operation.subscription.delivery
        ente_code = self.profile.siebel_entecode

        try:
            xdata = {
                'tem:cod_ente': ente_code,
                'tem:cod_suscripcion': id_delivery,  # id_delivery, siebel_delivery
                'tem:monto_cobrado': format(self.operation.amount, ".2f"),
                'tem:num_operacion': self.operation.payu_order_id,
                'tem:fch_hra_cobro': self.get_date_payment(self.operation),
                'tem:num_liquida_id': self.operation.payu_transaction_id,
                'tem:medio_de_pago': self.operation.payment_source_type,
                'tem:cod_pasarelaPago': 1,
                'tem:nro_renovacion': '',
                'tem:folio': '',
                'tem:cod_interno': ''
            }
            if test_mode:
                print(xdata)
            else:
                xml = soap_utils.soap.prepareConciliacion({'xdata': xdata})
                response = soap_utils.soap.sendConciliacion(xml)
                ########### save payment ############################3
                self.siebel_payment.siebel_request = xml
                self.siebel_payment.siebel_response = response
                self.siebel_payment.cod_response = True if response.get('Cod_Response', '') else False
                if not self.siebel_payment.siebel_hits:
                    self.siebel_payment.siebel_hits = 1
                else:
                    self.siebel_payment.siebel_hits += 1
                self.siebel_payment.save()
                ########### end save payment ############################3
                self.operation.siebel_payment = self.siebel_payment
                self.operation.save()

                self.log_siebel_conciliacion.log_request = xml
                self.log_siebel_conciliacion.log_response = response
                self.log_siebel_conciliacion.save()
                print(self.operation.payu_transaction_id)

        except Exception as e:
            print(e)
            with push_scope() as scope:
                scope.set_tag("external_tx_id", self.operation.external_tx_id)
                scope.level = 'warning'
                capture_event(
                    {
                        'message': 'payment_not_send',
                        'extra': {
                            'external_tx_id': self.operation.external_tx_id,
                            'error': e
                        }
                    }
                )