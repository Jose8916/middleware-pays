
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import csv


class Command(BaseCommand):
    help = 'filtra las suscripciones dobles, triples, etc'
    """
        python3 manage.py filter_unic_double --rama 'sandbox'
        python3 manage.py filter_unic_double --rama 'production' --dobles 1
    """
    def add_arguments(self, parser):
        parser.add_argument('--rama', nargs='?', type=str)
        parser.add_argument('--dobles', nargs='?', type=str)
        parser.add_argument('--triples', nargs='?', type=str)
        parser.add_argument('--cuadruples', nargs='?', type=str)
        parser.add_argument('--unicos', nargs='?', type=str)

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration'
        path_export = '/home/milei/Documentos/subscription_migration/production/tercera carga/triples_23jun.csv'.format(
            path=path,
            rama=options['rama']
        )
        path_source = '/home/milei/Documentos/subscription_migration/production/tercera carga/carga_tokens.csv'.format(
            path=path,
            rama=options['rama']
        )
        list_uuid = []

        if options['dobles'] or options['triples'] or options['cuadruples']:
            with open(path_source) as csvfilecount:
                reader_x = csv.DictReader(csvfilecount)
                for row in reader_x:
                    list_uuid.append(row.get('user_id', ''))

        with open(path_export, 'a', encoding="utf-8") as csvFileWrite:
            writer = csv.writer(csvFileWrite)
            writer.writerow(
                [
                    'user_id',
                    'email'
                ]
            )
            """
            writer.writerow(
                [
                    'user_id',
                    'term_id',
                    'customer_id',
                    'start_date',
                    'next_billing_date',
                    'prev_billing_date',
                    'payment_method_token',
                    'card_id',
                    'custom_billing_plan',
                    'auto_renew',
                    'provider_input_params',
                    'expiration',
                    'suscription_id',
                    'price_code',
                    'sku'
                ]
            )
            """

            with open(path_source) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if options['unicos']:
                        if row.get('user_id', '') not in list_uuid:
                            list_uuid.append(row.get('user_id', ''))
                            writer.writerow(
                                [
                                    row.get('user_id', ''),
                                    row.get('email', ''),
                                ]
                            )
                            """
                            writer.writerow(
                                [
                                    row.get('user_id', ''),
                                    row.get('term_id', ''),
                                    row.get('customer_id', ''),
                                    row.get('start_date', ''),
                                    row.get('next_billing_date', ''),
                                    row.get('prev_billing_date', ''),
                                    row.get('payment_method_token', ''),
                                    row.get('card_id', ''),
                                    row.get('custom_billing_plan', ''),
                                    row.get('auto_renew', ''),
                                    row.get('provider_input_params', ''),
                                    row.get('expiration', ''),
                                    row.get('suscription_id', ''),
                                    row.get('price_code', ''),
                                    row.get('sku', ''),
                                ]
                            )
                            """
                    elif options['dobles']:
                        if list_uuid.count(row.get('user_id', '')) == 2:
                            writer.writerow(
                                [
                                    row.get('user_id', ''),
                                    row.get('term_id', ''),
                                    row.get('customer_id', ''),
                                    row.get('start_date', ''),
                                    row.get('next_billing_date', ''),
                                    row.get('prev_billing_date', ''),
                                    row.get('payment_method_token', ''),
                                    row.get('card_id', ''),
                                    row.get('custom_billing_plan', ''),
                                    row.get('auto_renew', ''),
                                    row.get('provider_input_params', ''),
                                    row.get('expiration', ''),
                                    row.get('suscription_id', ''),
                                    row.get('price_code', ''),
                                    row.get('sku', ''),
                                ]
                            )
                    elif options['triples']:
                        if list_uuid.count(row.get('user_id', '')) == 3:
                            writer.writerow(
                                [
                                    row.get('user_id', ''),
                                    row.get('term_id', ''),
                                    row.get('customer_id', ''),
                                    row.get('start_date', ''),
                                    row.get('next_billing_date', ''),
                                    row.get('prev_billing_date', ''),
                                    row.get('payment_method_token', ''),
                                    row.get('card_id', ''),
                                    row.get('custom_billing_plan', ''),
                                    row.get('auto_renew', ''),
                                    row.get('provider_input_params', ''),
                                    row.get('expiration', ''),
                                    row.get('suscription_id', ''),
                                    row.get('price_code', ''),
                                    row.get('sku', ''),
                                ]
                            )
                    elif options['cuadruples']:
                        if list_uuid.count(row.get('user_id', '')) == 4:
                            writer.writerow(
                                [
                                    row.get('user_id', ''),
                                    row.get('term_id', ''),
                                    row.get('customer_id', ''),
                                    row.get('start_date', ''),
                                    row.get('next_billing_date', ''),
                                    row.get('prev_billing_date', ''),
                                    row.get('payment_method_token', ''),
                                    row.get('card_id', ''),
                                    row.get('custom_billing_plan', ''),
                                    row.get('auto_renew', ''),
                                    row.get('provider_input_params', ''),
                                    row.get('expiration', ''),
                                    row.get('suscription_id', ''),
                                    row.get('price_code', ''),
                                    row.get('sku', ''),
                                ]
                            )
            csvfile.close()

        return 'completado'
