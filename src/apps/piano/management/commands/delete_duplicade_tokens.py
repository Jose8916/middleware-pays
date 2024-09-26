
# -*- coding: utf-8 -*-

from django.core.management.base import BaseCommand
import csv


class Command(BaseCommand):
    help = 'filtra las suscripciones dobles, triples, etc'
    """
        python3 manage.py filter_unic_double.py --rama 'sandbox'
        python3 manage.py filter_unic_double.py --rama 'production'
    """
    def add_arguments(self, parser):
        parser.add_argument('--rama', nargs='?', type=str)

    def handle(self, *args, **options):
        path = '/home/milei/Documentos/subscription_migration'
        path_export = '/home/milei/Escritorio/payu/un_solo_uid.csv'.format(
            path=path,
            rama=options['rama']
        )
        path_export2 = '/home/milei/Escritorio/payu/mas_de_un_uid.csv'.format(
            path=path,
            rama=options['rama']
        )

        path_backup_source = '/home/milei/Escritorio/payu/union.csv'.format(
            path=path,
            rama=options['rama']
        )

        with open(path_export2, 'a', encoding="utf-8") as csvFileWrite2:
            writerx = csv.writer(csvFileWrite2)
            writerx.writerow(
                [
                    'user_id',
                    'customer_id',
                    'payment_method_token',
                    'card_id',
                    'provider_input_params',
                    'suscription_id'
                ]
            )
            with open(path_export, 'a', encoding="utf-8") as csvFileWrite:
                writer = csv.writer(csvFileWrite)
                writer.writerow(
                    [
                        'user_id',
                        'customer_id',
                        'payment_method_token',
                        'card_id',
                        'provider_input_params'
                    ]
                )
                list_uuid = []
                with open(path_backup_source) as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        list_uuid.append(row.get('uid', ''))

                with open(path_backup_source) as csvfile1:
                    reader1 = csv.DictReader(csvfile1)
                    for rows in reader1:
                        if list_uuid.count(rows.get('uid', '')) == 1:
                            writer.writerow(
                                [
                                    rows.get('uid', ''),
                                    rows.get('hub_customer_id', ''),
                                    rows.get('hub_token', ''),
                                    '',
                                    ''
                                ]
                            )
                        else:
                            writerx.writerow(
                                [
                                    rows.get('uid', ''),
                                    rows.get('hub_customer_id', ''),
                                    rows.get('hub_token', ''),
                                    '',
                                    '',
                                    rows.get('subscription_id', '')
                                ]
                            )
                csvfile1.close()

        return 'completado'
