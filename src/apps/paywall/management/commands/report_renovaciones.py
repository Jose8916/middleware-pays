from django.core.management.base import BaseCommand
from apps.paywall.models import Operation, FinancialTransaction, Subscription
from datetime import date, timedelta, datetime
from django.utils.encoding import smart_str
import csv
import json
import ast
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
    help = 'Visualiza las renovaciones de Ordenes de venta'
    # python manage.py report_renovaciones --periodo
    # python manage.py report_renovaciones --start 67 --end 97

    def add_arguments(self, parser):
        parser.add_argument('--lista_delivery', nargs='?', type=str)
        parser.add_argument('--payments', nargs='?', type=str)
        parser.add_argument('--end', nargs='?', type=str)
        parser.add_argument('--start', nargs='?', type=str)

    def handle(self, *args, **options):
        ahora = datetime.utcnow() - timedelta(days=int(options.get('end')))
        name_ = str(ahora.day) + '-' + str(ahora.month)
        last_month = ahora - timedelta(days=int(options.get('start')))

        if options.get('lista_delivery'):
            list_deliverys = ['668585', '668599', '668612', '668688', '668714', '668720', '668731', '668754', '669192',
                              '669257', '669426', '669442', '669472', '669517', '669531', '669635', '669774', '669900',
                              '669947', '670656', '670789', '670797', '670803', '670820', '670844', '670971', '671093',
                              '671097', '671225', '671232', '671233', '671345', '671376', '671383', '671392', '671398',
                              '671433', '671443', '671446', '672350', '672376', '672387', '672411', '672450', '672478',
                              '672515', '672597', '672625', '672648', '672652', '672667', '672674', '672683']
        else:
            list_deliverys = []
            subscriptions = Subscription.objects.filter(
                delivery__isnull=False,
                created__range=[last_month, ahora]
            )
            for obj in subscriptions:
                list_deliverys.append(obj.delivery)

        with open('/tmp/usuarios_renovaciones' + name_ + '.csv', 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([
                smart_str(u"Subscription Id"),
                smart_str(u"Delivery"),
                smart_str(u"num_liquida_id - TransactionId PAYU - sent"),
                smart_str(u"Monto"),
                smart_str(u"monto_enviado"),
                smart_str(u"Fecha de Pago"),
                smart_str(u"Plan"),
                smart_str(u"Pago enviado a Siebel"),
                smart_str(u"Nombre del promocion siebel"),
                smart_str(u"tipo - (1er pago o recurrencia)"),
                smart_str(u"Estado de renovacion"),
                smart_str(u"Fecha inicio renovacion"),
            ])
            for delivery_item in list_deliverys:
                users = Operation.objects.filter(
                    payment__subscription__delivery=delivery_item
                )

                for obj in users:
                    try:
                        arc_id = obj.payment.subscription.arc_id
                    except Exception as e:
                        arc_id = ''

                    try:
                        if obj.siebel_delivery:
                            delivery = obj.siebel_delivery
                        else:
                            delivery = obj.payment.subscription.delivery
                    except Exception as e:
                        delivery = ''

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

                    try:
                        monto = obj.payment.pa_amount
                    except Exception as e:
                        monto = ''

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

                    try:
                        fecha_pago = local_format(obj.payment.date_payment)
                    except Exception as e:
                        fecha_pago = ''

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

                    try:
                        estado_renovacion = ast.literal_eval(obj.recurrencia_request)
                        estado_renovacion = estado_renovacion.get('renovacion', '')
                    except Exception as e:
                        estado_renovacion = ''

                    try:
                        fch_ini_renovacion = ast.literal_eval(obj.recurrencia_request)
                        fch_ini_renovacion = fch_ini_renovacion.get('fchIniRenovacion', '')
                    except Exception as e:
                        fch_ini_renovacion = ''

                    row = [
                        arc_id,
                        delivery,
                        num_liquida_id_sent,
                        monto,
                        monto_enviado,
                        fecha_pago,
                        plan_name,
                        estado_pago,
                        prod_prom_name,
                        recurrence_value,
                        estado_renovacion,
                        fch_ini_renovacion
                    ]
                    writer.writerow(row)
                writer.writerow(['', '', '', '', '', '', '', '', '', ''])
        csvFile.close()
        print('exito')




















