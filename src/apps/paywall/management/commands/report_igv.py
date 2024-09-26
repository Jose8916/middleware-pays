from django.core.management.base import BaseCommand
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from apps.siebel.models import LoadTransactionsIdSiebel, SiebelConfirmationPayment, LogSiebelOv
from datetime import date, timedelta, datetime
from django.utils.encoding import smart_str
import csv
from django.utils.timezone import get_default_timezone


def local_format(_date):
    try:
        if not isinstance(_date, datetime):
            return ''

        _date = _date.astimezone(
            get_default_timezone()
        )

        _date = _date.replace(tzinfo=None)

        return _date
    except Exception as e:
        return ''
    except SystemExit:
        return ''


class Command(BaseCommand):
    help = 'Ejecuta el comando'
    # python manage.py report_igv --lista_payments 1 --opcion comando

    def add_arguments(self, parser):
        parser.add_argument('--end', nargs='?', type=str)
        parser.add_argument('--start', nargs='?', type=str)
        parser.add_argument('--lista_payments', nargs='?', type=str)
        parser.add_argument('--opcion', nargs='?', type=str)

    def get_transaction_id(self, obj):
        try:
            # transaction_id = obj.payment.payment_financial_transaction.transaction_id
            payu_ope = FinancialTransaction.objects.get(
                order_number=obj.payment.arc_order
            )
            transaction_id = payu_ope.transaction_id
        except Exception:
            transaction_id = ''
        return transaction_id

    def get_fecha_pago(self, obj):
        try:
            fecha_pago = local_format(obj.payment.date_payment)
        except Exception as e:
            fecha_pago = ''
        return fecha_pago

    def get_first_payment(self, obj):
        first_payment = 'No es el primer pago'
        operation_obj = Operation.objects.filter(
            payment__subscription__arc_id=obj.payment.subscription.arc_id,
            ope_amount__gte=5
        ).order_by('payment__transaction_date').first()

        if operation_obj.payment.payu_transaction == obj.payment.payu_transaction:
            first_payment = 'Primer pago'
        return first_payment

    def get_arc_id(self, obj):
        try:
            arc_id = obj.payment.subscription.arc_id
        except Exception as e:
            arc_id = ''
        return arc_id

    def get_last_send_ov(self, obj):
        try:
            log_ov = LogSiebelOv.objects.filter(operation=obj).last()
            return log_ov.created
        except Exception as e:
            return ''

    def get_payment_confirmation(self, obj):
        if SiebelConfirmationPayment.objects.filter(operation=obj).exists():
            return 'Recepcionado'
        else:
            return 'No recepcionado'

    def get_siebel_entecode(self, obj):
        try:
            siebel_entecode = obj.payment_profile.siebel_entecode
        except Exception:
            siebel_entecode = ''
        return siebel_entecode

    def get_resumen(self, siebel_entecode, delivery):
        if not siebel_entecode:
            resumen = 'no se creo entecode'
        elif not delivery:
            resumen = 'no se creo delivery'
        else:
            resumen = ''
        return resumen

    def get_delivery(self, obj):
        try:
            if obj.siebel_delivery:
                delivery = obj.siebel_delivery
            else:
                delivery = obj.payment.subscription.delivery
        except Exception as e:
            delivery = ''
        return delivery

    def get_payment_profile(self, obj):
        try:
            if not obj.payment_profile.siebel_entecode:
                ente_envio = obj.payment_profile.siebel_request
                ente_respuesta = obj.payment_profile.siebel_response
            else:
                ente_envio = ''
                ente_respuesta = ''
        except Exception:
            ente_envio = ''
            ente_respuesta = ''

        return ente_envio, ente_respuesta

    def get_envio_respuesta_ov(self, obj, delivery):
        if delivery:
            ov_pedido = ''
            ov_respuesta = ''
        else:
            try:
                ov_pedido = obj.siebel_request
                ov_respuesta = obj.siebel_response
            except Exception as e:
                ov_pedido = e
                ov_respuesta = ''
        return ov_pedido, ov_respuesta

    def get_monto(self, obj):
        try:
            monto = obj.payment.pa_amount
        except Exception as e:
            monto = ''
        return monto

    def handle(self, *args, **options):
        if options.get('lista_payments') and options.get('opcion'):
            ahora = datetime.utcnow()
            name_ = str(ahora.day) + '-' + str(ahora.month) + '-' + str(ahora.hour)
            opcion = options.get('opcion')
            transaction = LoadTransactionsIdSiebel.objects.get(tipo=opcion)
            transactions = transaction.transaction_id
            list_transactions = transactions.splitlines()
        else:
            ahora = datetime.utcnow() - timedelta(days=int(options.get('end')))
            name_ = str(ahora.day) + '-' + str(ahora.month)
            last_month = ahora - timedelta(days=int(options.get('start')))

        print(list_transactions)
        with open('/tmp/usuarios_renovaciones' + name_ + '.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([
                smart_str(u"Resumen"),
                smart_str(u"Subscription Id"),
                smart_str(u"Trama Envio ENTECODE"),
                smart_str(u"Trama Respuesta ENTECODE"),
                smart_str(u"Delivery"),
                smart_str(u"Trama Envio Ov"),
                smart_str(u"Trama Respuesta Ov"),
                smart_str(u"num_liquida_id - TransactionId PAYU - sent"),
                smart_str(u"Transaction Id"),
                smart_str(u"Monto"),
                smart_str(u"monto_enviado"),
                smart_str(u"Fecha de Pago"),
                smart_str(u"Plan"),
                smart_str(u"Pago enviado a Siebel"),
                smart_str(u"Nombre del promocion siebel"),
                smart_str(u"tipo - (web o recurrence)"),
                smart_str(u"primer pago(diferente de cero)"),
                smart_str(u"ultimo envio a siebel"),
                smart_str(u"confirmacion de pago"),
            ])

            if options.get('lista_payments'):
                users = Operation.objects.filter(
                    payment__payment_financial_transaction__transaction_id__in=list_transactions
                )
            else:
                users = Operation.objects.filter(
                    conciliation_cod_response="1",
                    created__range=[last_month, ahora]
                )

            print(users)
            print(options.get('lista_payments'))
            for obj in users:
                first_payment = self.get_first_payment(obj)
                print(first_payment)
                if first_payment != 'Primer pago':
                    operations = Operation.objects.filter(
                        payment__subscription__arc_id=obj.payment.subscription.arc_id,
                        ope_amount__gte=5
                    ).order_by('created')
                    for op in operations:
                        delivery = self.get_delivery(op)
                        ov_pedido, ov_respuesta = self.get_envio_respuesta_ov(op, delivery)
                        ente_envio, ente_respuesta = self.get_payment_profile(op)
                        siebel_entecode = self.get_siebel_entecode(op)
                        resumen = self.get_resumen(siebel_entecode, delivery)
                        transaction_id = self.get_transaction_id(op)
                        fecha_pago = self.get_fecha_pago(op)

                        row = [
                            resumen,
                            self.get_arc_id(op),
                            ente_envio,
                            ente_respuesta,
                            delivery,
                            ov_pedido,
                            ov_respuesta,
                            '',
                            transaction_id,
                            self.get_monto(op),
                            '',
                            fecha_pago,
                            '',
                            '',
                            '',
                            '',
                            self.get_first_payment(op),
                            self.get_last_send_ov(op),
                            self.get_payment_confirmation(op)
                        ]
                        writer.writerow(row)
                arc_id = self.get_arc_id(obj)

                delivery = self.get_delivery(obj)

                try:
                    if obj.conciliation_siebel_request:
                        start = '<tem:num_liquida_id>'
                        end = '</tem:num_liquida_id>'
                        csr = obj.conciliation_siebel_request
                        num_liquida_id_sent = csr[csr.find(start) + len(start):csr.find(end)]
                    else:
                        num_liquida_id_sent = ''
                except Exception as e:
                    num_liquida_id_sent = ''

                monto = self.get_monto(obj)

                try:
                    if obj.conciliation_siebel_request:
                        start = '<tem:monto_cobrado>'
                        end = '</tem:monto_cobrado>'
                        csr = obj.conciliation_siebel_request
                        monto_enviado = csr[csr.find(start) + len(start):csr.find(end)]
                    else:
                        monto_enviado = ''
                except Exception as e:
                    monto_enviado = ''

                fecha_pago = self.get_fecha_pago(obj)

                try:
                    plan_name = obj.payment.subscription.plan.plan_name
                except Exception as e:
                    plan_name = ''

                try:
                    if obj.conciliation_cod_response == '1':
                        estado_pago = 'Enviado'
                    else:
                        estado_pago = 'No Enviado'
                except Exception as e:
                    estado_pago = 'No Enviado'

                try:
                    if obj.siebel_request:
                        start = '<eco:ProdPromName>'
                        end = '</eco:ProdPromName>'
                        s = obj.siebel_request
                        prod_prom_name = s[s.find(start) + len(start):s.find(end)]
                    else:
                        prod_prom_name = ''
                except Exception as e:
                    prod_prom_name = ''

                try:
                    if obj.payment.pa_origin == 'WEB':
                        recurrence_value = 'Primera Venta'
                    else:
                        recurrence_value = 'Recurrencia'
                except Exception as e:
                    recurrence_value = ''

                ov_pedido, ov_respuesta = self.get_envio_respuesta_ov(obj, delivery)
                ente_envio,  ente_respuesta = self.get_payment_profile(obj)
                siebel_entecode = self.get_siebel_entecode(obj)
                resumen = self.get_resumen(siebel_entecode, delivery)
                transaction_id = self.get_transaction_id(obj)

                row = [
                    resumen,
                    arc_id,
                    ente_envio,
                    ente_respuesta,
                    delivery,
                    ov_pedido,
                    ov_respuesta,
                    num_liquida_id_sent,
                    transaction_id,
                    monto,
                    monto_enviado,
                    fecha_pago,
                    plan_name,
                    estado_pago,
                    prod_prom_name,
                    recurrence_value,
                    first_payment,
                    self.get_last_send_ov(obj),
                    self.get_payment_confirmation(obj)
                ]
                writer.writerow(row)
        csvFile.close()
        print('exito')




















