# -*- coding: utf-8 -*-
import datetime

from django.core.management.base import BaseCommand
from apps.piano.models import Transaction
from django.conf import settings
from apps.siebel.models import SiebelConfirmationPayment


def dehydrate_llegada_de_comprobantes(transaction):
    try:
        confirmation = SiebelConfirmationPayment.objects.get(num_liquidacion=transaction.payu_transaction_id)
        return confirmation.created
    except:
        return None


def dehydrate_con_pago(transaction):
    if transaction.siebel_payment:
        if transaction.siebel_payment.cod_response:
            return 'con pago'

    return 'sin pago'


def get_transactions(from_datetime, until_datetime, brand):
    if from_datetime and until_datetime:
        transactions = Transaction.objects.filter(created__gte=from_datetime, created__lte=until_datetime,
                                                  term__app_id=settings.PIANO_APPLICATION_ID[brand])
    elif not from_datetime and until_datetime:
        transactions = Transaction.objects.filter(created__lte=until_datetime,
                                                  term__app_id=settings.PIANO_APPLICATION_ID[brand])
    elif from_datetime and not until_datetime:
        transactions = Transaction.objcts.filter(created__gte=from_datetime,
                                                 term__app_id=settings.PIANO_APPLICATION_ID[brand])
    else:
        transactions = Transaction.objects.filter(term__app_id=settings.PIANO_APPLICATION_ID[brand])
    return transactions


class Command(BaseCommand):
    help = 'Ejecuta el comando para obetener reporte de transacciones'

    def add_arguments(self, parser):
        parser.add_argument('-br', '--brand', nargs='?', type=str, help='marca: elcomercio, gestion')
        parser.add_argument('-fd', '--from_datetime', nargs='?', type=str, help='Fecha y hora desde que se va a obtener transacciones')
        parser.add_argument('-ud', '--until_datetime', nargs='?', type=str, help='Fechay hora hasta cuando se va a obtener transacciones')

    def handle(self, *args, **options):
        name_file = 'report_todas_las_transacciones'
        brand = options.get('brand')
        path_file = f"{settings.BASE_DIR}/{name_file}_{brand}.csv"
        titles = "Email,Suscripcion Id,entecode,delivery,external_tx_id,payu_transaction_id,llegada_de_comprobantes,con_pago,uid,term_id,term_transaction_name,tern_name,term_description,payu_order_id,marca\n"

        with open(path_file, "w", encoding="utf-8") as outfile:
            outfile.write(titles)
            try:
                from_datetime = datetime.datetime.strptime(options.get('from_datetime'), '%Y-%m-%dT%H:%M:%S')
                until_datetime = datetime.datetime.strptime(options.get('until_datetime'), '%Y-%m-%dT%H:%M:%S')
                transactions = get_transactions(from_datetime, until_datetime, brand)
            except Exception as e:
                print(e)
            print(path_file)
            print(len(transactions))
            print('inicio')
            for t in transactions.iterator():
                try:
                    email = t.subscription.payment_profile.portal_email
                except Exception:
                    email = None
                subscription_id = t.subscription_id_str
                try:
                    entecode = t.subscription.payment_profile.siebel_entecode
                except Exception:
                    entecode = None
                # log_envio_delivery = t.siebel_sale_order.siebel_request if t.siebel_sale_order else None
                # log_request_delivery = t.siebel_sale_order.siebel_response if t.siebel_sale_order else None
                try:
                    delivery = t.subscription.delivery
                except Exception:
                    delivery = None
                external_tx_id = t.external_tx_id
                payu_transaction_id = t.payu_transaction_id
                llegada_de_comprobantes = dehydrate_llegada_de_comprobantes(t)
                pago = dehydrate_con_pago(t)
                user_id = t.user_id
                term_id = t.term.term_id
                term_transaction_name = t.term_name
                term_name = t.term.plan_name
                term_description = t.term.plan_description
                payu_order_id = t.payu_order_id
                marca = brand
                row = f'{email},{subscription_id},{entecode},{delivery},{external_tx_id},{payu_transaction_id},{llegada_de_comprobantes},{pago},{user_id},{term_id},{term_transaction_name},{term_name},{term_description},{payu_order_id},{marca}\n'
                outfile.write(row)
            print('fin')





