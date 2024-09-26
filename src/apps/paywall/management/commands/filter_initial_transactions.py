
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import csv


class Command(BaseCommand):
    help = 'Del archivo de backup csv filtra solo los primeros pagos'
    """
        python3 manage.py filter_initial_transactions --rama 'sandbox'
        python3 manage.py filter_initial_transactions --rama 'production'
    """
    def add_arguments(self, parser):
        parser.add_argument('--rama', nargs='?', type=str)

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration'
        path_backup = '{path}/{rama}/backup_subscriptions.csv'.format(
            path=path,
            rama=options['rama']
        )
        path_backup_source = '{path}/{rama}/backup_subscriptions_with_payments.csv'.format(
            path=path,
            rama=options['rama']
        )
        with open(path_backup, 'a', encoding="utf-8") as csvFileWrite:
            writer = csv.writer(csvFileWrite)
            writer.writerow(
                [
                    'country',
                    'lastName',
                    'periodTo',
                    'secondLastName',
                    'amount',
                    'orderNumber',
                    'clientId',
                    'periodFrom',
                    'tax',
                    'financialTransactionId',
                    'createdOn',
                    'transactionType',
                    'firstName',
                    'initialTransaction',
                    'providerReference',
                    'currency',
                    'subscriptionId',
                    'sku',
                    'line2'
                ]
            )

            with open(path_backup_source) as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if row.get('initialTransaction', '') == 'True':
                        writer.writerow(
                            [
                                row.get('country', ''),
                                row.get('lastName', ''),
                                row.get('periodTo', ''),
                                row.get('secondLastName', ''),
                                row.get('amount', ''),
                                row.get('orderNumber', ''),
                                row.get('clientId', ''),
                                row.get('periodFrom', ''),
                                row.get('tax', ''),
                                row.get('financialTransactionId', ''),
                                row.get('createdOn', ''),
                                row.get('transactionType', ''),
                                row.get('firstName', ''),
                                row.get('initialTransaction', ''),
                                row.get('providerReference', ''),
                                row.get('currency', ''),
                                row.get('subscriptionId', ''),
                                row.get('sku', ''),
                                row.get('line2', '')
                            ]
                        )
            csvfile.close()

        return 'completado'
