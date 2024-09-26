
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import csv


class Command(BaseCommand):
    help = 'filtra las suscripciones dobles, triples, etc'
    """
        python3 manage.py filer_subscriptions_double --rama 'sandbox'
        python3 manage.py filer_subscriptions_double --rama 'production'
    """
    def add_arguments(self, parser):
        parser.add_argument('--rama', nargs='?', type=str)

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration'
        path_backup = '{path}/{rama}/cuadruples.csv'.format(
            path=path,
            rama=options['rama']
        )
        path_backup_source = '{path}/{rama}/Enoqbpnkpu_subs_payu.csv'.format(
            path=path,
            rama=options['rama']
        )
        with open(path_backup, 'a', encoding="utf-8") as csvFileWrite:
            writer = csv.writer(csvFileWrite)
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
            list_uuid = []
            with open(path_backup_source) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    list_uuid.append(row.get('user_id', ''))

            with open(path_backup_source) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
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
